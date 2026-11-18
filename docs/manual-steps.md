# Steps a person has to do once per new AWS account

Terraform cannot do these. They came up while building in a fresh AWS account on 13 November 2026.

1. **Red Hat login.** `rosa login --use-device-code`. The login expires after a while; the old
   service account in `.env` is rejected by Red Hat.
2. **Link the account to the Red Hat organisation.** `make link-account` creates and links the
   OCM role and the user role. Without it the cluster request fails with 403.
3. **Enable ROSA in the AWS console and link billing.** In the AWS console open
   "Red Hat OpenShift Service on AWS", choose "Get started", enable ROSA with hosted control
   planes and follow "Continue to Red Hat" to connect the AWS account with the Red Hat account.
   Without it the cluster request fails with 400: "billing account not linked to organization
   at the aws marketplace". This accepts AWS Marketplace terms, so the account owner does it.
