# GCP Permissions Watchdog

**Public Dashboard for Tracking GCP IAM Permission History**

This project tracks the complete history of *all available* Google Cloud Platform (GCP) IAM permissions. It serves as a public resource to visualize when specific permissions were added, removed, or modified by Google.

**[View the Dashboard](https://exe-cut3.github.io/gcp-permissions-watchdog/)**

It works by analyzing daily snapshots from [gcp-permissions-checker](https://github.com/exe-cut3/gcp-permissions-checker) to highlight changes over time.

### Features

- **Provider-Level Tracking**: Tracks the entire catalog of ~12,000+ IAM permissions exposed by Google.
- **Historical Timeline**: Browse snapshots to see exactly when new services or permissions were introduced.
- **Deep Diffing**: See the exact difference in permission sets between any two dates.

---

*Powered by GitHub Actions & GitHub Pages.*
