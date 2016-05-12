# Stages of Integration

When integrating third-party software with Cloud Foundry, the integration
typically progresses through the same set of stages. We recommend this
staged approach because it enables early feedback on the value and the
design of the integration, which helps make better decisions about future
stages.

For service type integrations, the typical stages of integration are:

1. User-Provided Service
2. Brokered Service
3. Managed Service
4. Dynamic Service

Each of these is described in more detail below. In general, user-experience
and production-readiness improves as the integration
progresses through the stages. But none of the later stages is required.
Integration can stop and be declared complete (enough) after any of these.

For non-service integrations (such as applications or buildpacks), a similar
staged integration approach is often possible and desirable.

## Stage 1 - User-Provided Service

Either your software is available as a SaaS-offering, or you already have a
way to install software on-premise at a customer site. Or also likely, your
customer already has your software, is now adopting PCF, and wants to be
able to consume your software from applications deployed on PCF.

In most cases, customers can immediately start consuming your software from
their PCF applications through the user-provided service mechanism available
in Cloud Foundry. Tell them to create a user-provided service in their
application org and space using the command:

```bash
cf create-user-provided-service <my-service-name> -p <credentials>'
```

or `cf cups` for short. The `<credentials>` argument should be a valid JSON
string that contains the URL and credentials necessary to connect to your
externally-deployed service.

By doing this, application developers can bind
to your service and write all code necessary to access it through a Cloud
Foundry service binding. It is a great way to determine what information
needs to be passed in the credential structure (useful in later integration
stages), verify that the integration works, and develop a test application
that can continue to be used for later stages. And from the application
developer perspective, once this works, later stages will not require any
further code changes. User-provided service bindings are fully compatible with
brokered service bindings.

## Stage 2 - Brokered Service

## Stage 3 - Managed Service

## Stage 3b - High Availability

## Stage 4 - Dynamic Service

## Stage 4b - High Availability
