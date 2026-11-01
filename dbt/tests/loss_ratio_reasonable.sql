-- Paid should not exceed 5× premium per county per year.
SELECT county, YEAR(claim_date) AS y, SUM(paid_amount) AS paid, SUM(premium) AS premium
FROM {{ ref('fact_claims') }}
GROUP BY 1, 2
HAVING SUM(paid_amount) > 5 * SUM(premium)