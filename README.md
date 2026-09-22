# Investor News Feed — Retired

This repository is retired from the active Central Intelligence architecture.

The Central Intelligence application now uses:

```text
central-intelligence-dashboard
        ↓
     Supabase
        ↓
central-intelligence-ui
        ↓
      Vercel
```

News collection, processing, sentiment analysis, and Supabase writes are handled by:

```text
rchern315/central-intelligence-dashboard
```

The frontend is:

```text
rchern315/central-intelligence-ui
```

Production application:

https://central-intelligence-ui.vercel.app/

The RSS generator in this repository is preserved for historical/reference purposes but is no longer part of the active application data flow.

Scheduled feed generation has been disabled.
