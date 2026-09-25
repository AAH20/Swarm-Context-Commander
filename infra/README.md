# Infrastructure examples

`terraform/` is a small **configuration-only** Kubernetes module. It creates a namespace and admission ConfigMap. It has no provider credentials or remote backend configuration; the operator must supply those and protect Terraform state. It does not deploy a runnable service.

`kubernetes/` contains **non-deployable design examples** for KEDA queue scaling and a pinned vLLM GPU pool. The Redis address, worker Deployment, model path and image digest are placeholders. Replace them and validate CRDs, GPU drivers, permissions, storage, queue behavior and graceful termination in a test cluster before deployment.

The target layering is: Terraform for durable resources → KEDA/HPA for CPU workers → measured warm GPU pool plus model-specific scaling → immediate scheduler admission and backpressure. MicroVM and Google/AX runtime backends require separately implemented lifecycle controllers.
