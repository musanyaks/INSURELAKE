# INSURELAKE - Executive Control Centre (Next.js)

    cd dashboard/web
    npm install
    npm run dev        # http://localhost:3100

Requires Node >= 18.17.

Optional live data from the FastAPI service:

    NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev

Every query falls back to mock data if the endpoint is unreachable.
