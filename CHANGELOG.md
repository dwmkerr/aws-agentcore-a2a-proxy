# Changelog

## [0.1.1](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/compare/v0.1.0...v0.1.1) (2025-07-26)


### Features

* add CI/CD workflow with release-please and PyPI publishing ([5632138](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/5632138fc64545a852f266d78fe0a87a9272efd2))
* add Codecov token for reliable coverage uploads ([0fe6906](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/0fe6906ea5bc1b9180524a8c180fc1a34f68902c))
* add comprehensive agent polling and clean infrastructure ([cbeda60](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/cbeda60ddbb1dc846d181bd3dcc928a19a65c3e5))
* add comprehensive unit tests with 100% coverage for A2A proxy ([b85a783](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/b85a783a08fc7e12e531f107af256b22de4b27bf))
* add demo infrastructure with idiomatic Terraform ([6f4b11e](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/6f4b11eda79d323f97c38b1072324e51425ceced))
* configure CI/CD to publish to TestPyPI ([fe0328d](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/fe0328dc7803416a73f7d2376185b57da00b0bf0))
* extract AgentCoreHTTPClient and add comprehensive unit tests ([db8d000](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/db8d0008c24d5c492fb242f5e6477d9c9e94faa7))
* implement comprehensive streaming support for AgentCore invocations ([0310f00](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/0310f0066e9d5dc4fb659ae14c1bc008288a0203))
* init demo ([d38df01](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/d38df01dceb5d18c547f7d7500b86a24f40927d8))
* make Bedrock model configurable in Terraform ([293781e](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/293781e888f7d7482b88194eae5066957985b07f))
* reorganize API endpoints and enhance documentation ([b77d720](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/b77d720138e85b1ee75939028b3438b400a64a66))
* simplify streaming to use Bedrock native capabilities ([6c009fc](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/6c009fc4e80071918c61f9550cf30c7fca3a3fdb))


### Bug Fixes

* add missing workflow permissions for release-please ([3bf4ad6](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/3bf4ad6a61599aab7dbeca7e0fa8581b85b2bbbe))
* configure release-please versioning strategy for 0.x releases ([fd230d6](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/fd230d6e8c1f57acaac98e4091778e003aaf691c))
* correct release-please configuration ([3155a0d](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/3155a0de3d7161d317b5602dced6cff6821ef999))
* correct working directory paths in CI/CD workflow ([4e866cb](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/4e866cb3fab8f03c119940772ef5fad0cc557d2b))
* improve A2A response format translation and add TODO list ([abfac5b](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/abfac5b1ac6443164540d0088795d6acc6f18b9a))
* resolve all pyright type checking issues and enhance linting pipeline ([5b8ef9f](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/5b8ef9f443c2fe93f9da214010e0035a1c10a928))
* resolve dependency installation issues in CI/CD ([8be5d9e](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/8be5d9e7bde13ed30c666378b4c2016886317643))
* resolve Terraform IAM permissions and stale Dockerfile ([b0e5c84](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/b0e5c84083e5085eeba5bc1aaeef6a56c37d3dd6))


### Documentation

* add comprehensive streaming documentation and additional features section ([c03bc40](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/c03bc40f0b3c1abff06aa17bf91529f4e1acc9b4))
* add dynamic agent ID extraction using jq ([ef2480e](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/ef2480ebe6e9361a24faf1b526c59b9638a056ac))


### Miscellaneous Chores

* release 0.1.1 ([34d0a82](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/34d0a82af79d481dd5e14118d3b12dc7264096da))

## 0.1.0 (2025-07-26)


### Features

* add CI/CD workflow with release-please and PyPI publishing ([5632138](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/5632138fc64545a852f266d78fe0a87a9272efd2))
* add Codecov token for reliable coverage uploads ([0fe6906](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/0fe6906ea5bc1b9180524a8c180fc1a34f68902c))
* add comprehensive agent polling and clean infrastructure ([cbeda60](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/cbeda60ddbb1dc846d181bd3dcc928a19a65c3e5))
* add comprehensive unit tests with 100% coverage for A2A proxy ([b85a783](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/b85a783a08fc7e12e531f107af256b22de4b27bf))
* add demo infrastructure with idiomatic Terraform ([6f4b11e](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/6f4b11eda79d323f97c38b1072324e51425ceced))
* configure CI/CD to publish to TestPyPI ([fe0328d](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/fe0328dc7803416a73f7d2376185b57da00b0bf0))
* extract AgentCoreHTTPClient and add comprehensive unit tests ([db8d000](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/db8d0008c24d5c492fb242f5e6477d9c9e94faa7))
* implement comprehensive streaming support for AgentCore invocations ([0310f00](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/0310f0066e9d5dc4fb659ae14c1bc008288a0203))
* init demo ([d38df01](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/d38df01dceb5d18c547f7d7500b86a24f40927d8))
* make Bedrock model configurable in Terraform ([293781e](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/293781e888f7d7482b88194eae5066957985b07f))
* reorganize API endpoints and enhance documentation ([b77d720](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/b77d720138e85b1ee75939028b3438b400a64a66))
* simplify streaming to use Bedrock native capabilities ([6c009fc](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/6c009fc4e80071918c61f9550cf30c7fca3a3fdb))


### Bug Fixes

* correct working directory paths in CI/CD workflow ([4e866cb](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/4e866cb3fab8f03c119940772ef5fad0cc557d2b))
* improve A2A response format translation and add TODO list ([abfac5b](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/abfac5b1ac6443164540d0088795d6acc6f18b9a))
* resolve all pyright type checking issues and enhance linting pipeline ([5b8ef9f](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/5b8ef9f443c2fe93f9da214010e0035a1c10a928))
* resolve dependency installation issues in CI/CD ([8be5d9e](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/8be5d9e7bde13ed30c666378b4c2016886317643))
* resolve Terraform IAM permissions and stale Dockerfile ([b0e5c84](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/b0e5c84083e5085eeba5bc1aaeef6a56c37d3dd6))


### Documentation

* add comprehensive streaming documentation and additional features section ([c03bc40](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/c03bc40f0b3c1abff06aa17bf91529f4e1acc9b4))
* add dynamic agent ID extraction using jq ([ef2480e](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/ef2480ebe6e9361a24faf1b526c59b9638a056ac))
