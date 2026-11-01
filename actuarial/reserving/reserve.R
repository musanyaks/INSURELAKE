#!/usr/bin/env Rscript
# actuarial/reserving/reserve.R
#
# Usage:
#   Rscript reserve.R <claims_development.parquet> <fact_claims.parquet> <out_dir>
#
# Produces:
#   reserve_summary.parquet       - one row per method
#   mack_by_cohort.parquet        - per-cohort Mack SE
#   bf_by_cohort.parquet          - per-cohort BF reserve
#   cape_cod_by_cohort.parquet    - per-cohort Cape Cod reserve
#   reserve_summary.json          - human-readable summary

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(tidyr)
  library(tibble)
  library(ChainLadder)
  library(jsonlite)
})

args        <- commandArgs(trailingOnly = TRUE)
dev_path    <- if (length(args) >= 1) args[1] else "claims_development.parquet"
claims_path <- if (length(args) >= 2) args[2] else "fact_claims.parquet"
out_dir     <- if (length(args) >= 3) args[3] else "."
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

dev    <- arrow::read_parquet(dev_path)
claims <- arrow::read_parquet(claims_path)

# =====================================================================
# 1. Build the cumulative paid development triangle
# =====================================================================
max_dev <- 12L
tri_long <- dev %>%
  mutate(
    origin     = format(as.Date(claim_date), "%Y-%m"),
    dev_period = as.integer(dev_month) + 1L
  ) %>%
  filter(dev_period <= max_dev) %>%
  group_by(origin, dev_period) %>%
  summarise(paid = sum(paid_amount, na.rm = TRUE), .groups = "drop")

tri_wide <- tri_long %>%
  pivot_wider(names_from = dev_period, values_from = paid, values_fill = 0) %>%
  column_to_rownames("origin") %>%
  as.matrix()

# Cumulate across development columns
tri <- t(apply(tri_wide, 1, cumsum))

# Mask the unobserved lower-right triangle
n <- nrow(tri); m <- ncol(tri)
for (i in seq_len(n)) {
  latest_obs <- m - i + 1L
  if (latest_obs < 1L)          tri[i, ] <- NA
  else if (latest_obs < m)      tri[i, (latest_obs + 1L):m] <- NA
}

cat("Triangle:", n, "cohorts x", m, "dev periods\n")

# =====================================================================
# 2. Age-to-age factors, CDFs
# =====================================================================
link <- numeric(m - 1L)
for (j in seq_len(m - 1L)) {
  valid <- !is.na(tri[, j]) & !is.na(tri[, j + 1L])
  link[j] <- if (any(valid)) sum(tri[valid, j + 1L], na.rm = TRUE) /
                              sum(tri[valid, j],    na.rm = TRUE)
             else 1.0
}
cdf <- rev(cumprod(rev(c(link, 1.0))))  # cdf[k] = cumulative factor from dev k to ultimate

latest_dev <- apply(tri, 1L, function(x) {
  obs <- which(!is.na(x)); if (!length(obs)) NA_integer_ else max(obs)
})
latest_paid <- mapply(function(i, d) tri[i, d], seq_len(n), latest_dev)
row_cdf     <- cdf[pmin(latest_dev, length(cdf))]
unreported  <- pmax(1 - 1 / row_cdf, 0)

# =====================================================================
# 3. Chain Ladder (deterministic, we compute directly so the math is visible)
# =====================================================================
cl_ult   <- latest_paid * row_cdf
ibnr_cl  <- sum(cl_ult - latest_paid, na.rm = TRUE)
ult_cl   <- sum(cl_ult,               na.rm = TRUE)

# =====================================================================
# 4. Mack standard error
# =====================================================================
mack     <- ChainLadder::MackChainLadder(tri, est.sigma = "Mack")
mack_sum <- summary(mack)

# Totals is a data.frame; column names differ slightly across versions.
mack_se   <- tryCatch(as.numeric(mack_sum$Totals["Mack S.E.:", 1]), error = function(e) NA_real_)
ibnr_mack <- tryCatch(as.numeric(mack_sum$Totals["IBNR:", 1]),      error = function(e) ibnr_cl)
ult_mack  <- tryCatch(sum(mack$FullTriangle[, ncol(mack$FullTriangle)]), error = function(e) ult_cl)

# =====================================================================
# 5. Bornhuetter-Ferguson (with a priori loss ratio)
# =====================================================================
expected_lr <- 0.70

prem <- claims %>%
  mutate(origin = format(as.Date(claim_date), "%Y-%m")) %>%
  group_by(origin) %>%
  summarise(exposure = sum(premium, na.rm = TRUE), .groups = "drop")

bf_df <- tibble(
  origin   = rownames(tri),
  latest   = latest_paid,
  cdf      = row_cdf,
  exposure = prem$exposure[match(rownames(tri), prem$origin)]
) %>%
  mutate(
    exposure = ifelse(is.na(exposure) | exposure <= 0, latest, exposure),
    ultimate = latest + expected_lr * exposure * unreported,
    ibnr     = ultimate - latest
  )

# =====================================================================
# 6. Cape Cod (data-derived loss ratio, same mechanics as BF)
# =====================================================================
cc_lr <- sum(bf_df$latest, na.rm = TRUE) /
         sum(bf_df$exposure * unreported, na.rm = TRUE)

cc_df <- bf_df %>%
  mutate(
    ultimate_cc = latest + cc_lr * exposure * unreported,
    ibnr_cc     = ultimate_cc - latest
  )

# =====================================================================
# 7. Summary table
# =====================================================================
summary_tbl <- tibble(
  method         = c("ChainLadder", "Mack", "BornhuetterFerguson", "CapeCod"),
  ultimate_total = c(ult_cl, ult_mack, sum(bf_df$ultimate), sum(cc_df$ultimate_cc)),
  ibnr_total     = c(ibnr_cl, ibnr_mack, sum(bf_df$ibnr), sum(cc_df$ibnr_cc)),
  std_error      = c(NA, mack_se, NA, NA),
  a_priori_lr    = c(NA, NA, expected_lr, round(cc_lr, 4))
)

# =====================================================================
# 8. Persist
# =====================================================================
arrow::write_parquet(summary_tbl, file.path(out_dir, "reserve_summary.parquet"))
arrow::write_parquet(bf_df,       file.path(out_dir, "bf_by_cohort.parquet"))
arrow::write_parquet(cc_df,       file.path(out_dir, "cape_cod_by_cohort.parquet"))

mack_by_cohort <- tryCatch(as_tibble(mack_sum$ByOrigin, rownames = "origin"),
                           error = function(e) tibble())
arrow::write_parquet(mack_by_cohort, file.path(out_dir, "mack_by_cohort.parquet"))

write_json(
  list(
    generated_at        = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ"),
    triangle_cohorts    = n,
    triangle_dev_periods = m,
    a_priori_loss_ratio = expected_lr,
    cape_cod_loss_ratio = round(cc_lr, 4),
    summary             = summary_tbl
  ),
  file.path(out_dir, "reserve_summary.json"),
  pretty = TRUE, auto_unbox = TRUE
)

cat("\n=== Reserving summary ===\n")
print(summary_tbl)
cat("\nCape Cod implied loss ratio:", round(cc_lr, 4), "\n")