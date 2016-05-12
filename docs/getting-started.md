# Getting Started

As an Independent Software Vendor (ISV), you are likely to find more and more
Pivotal Cloud Foundry (PCF) users among your customers. Many of these will be
asking you to integrate your software with PCF to enable use of your software
with the applications they are developing on, or migrating to, PCF.

Pivotal is very supportive of these types of integrations and is committed to
making this process as easy as possible. This site provides a *technical*
overview on how to integrate your software with PCF. You are welcome to
start this process on your own, or [contact us](mailto:mjoseph@pivotal.io)
to ask for our support and/or publish your integration in our
[marketplace](network.pivotal.io).

There are a lot of things you will have to learn and do to complete an
integration with Cloud Foundry. This page attempts to lay out a typical
progression of an integration with PCF.

## Step 0. Understand the concepts

There are [many ways](integration-types.md) to integrate products with Cloud Foundry.
The right one for each product depends on what the product does, and how
customer applications consume it. To determine the best way to integrate your
product, you'll need a good understanding of
[Cloud Foundry concepts](cf-concepts.md)
like applications, containers, services, brokers, and buildpacks.

## Step 1. Design the integration

With sufficient understanding of both your product, and Cloud Foundry concepts,
you are in a position to decide what the integration looks like. Integration
points might include:

- Service Brokers
- Managed Services
- Buidlpacks
- Embedded Agents
- Or any combination of the above

If you are not intimately familiar with Cloud Foundry, this is one of the
areas where we can help. We like to do scoping meetings with you, where
we pair your understanding of your products, with our understanding of
Cloud Foundry, to map out the best possible integration path.

## Step 2. Learn how to build

Depending on the selected type of integration, you will need to learn
how to build on or more of:

- [Service brokers](service-brokers.md)
- [Managed services](managed-services.md)
- [Dynamic services](dynamic-services.md)
- [Buildpacks](buildpacks.md)
- [Embedded agents](embedded-agents.md)

Self-learning is definitely possible. If you are interested in more
organized learning, Pivotal provides many different classes and labs for
partners and customers. [Contact us](mailto:mjoseph@pivotal.io)
if your are interested in learning more about this.

## Step 3. Set up a test environment

Once you move into development, you will need access to a PCF environment.
Partners who participate in our program have access to a number of shared
environments that are operated and managed by Pivotal. If you are not (yet)
in our program, need a dedicated environment, or want to be able to work
offline, you can set up a PCF environment on:

- [Developer desktop/laptop](pcf-dev.md)
- [Supported public or private infrastructure (IaaS)](pcf-iaas.md)

You will then also need to learn to operate and upgrade PCF by yourself:

- [Operating a PCF environment](pcf-operations.md)
- [Upgrading a PCF environment](pcf-upgrade.md)

## Step 4. Validate the design

Pivotal is a strong believer in lean and agile development and the notion
of delivering a Minimally Viable Product (MVP) to our customers as quickly
as possible. So we always look for [staged approaches](stages.md) to
the development of the integration, and only plan the upcoming stage in
great detail.

In most cases, there is a very rapid way to do a proof-of-concept of the
proposed integration. For instance, if you are building a service, you
can often emulate the availability of a brokered, managed, or dynamic
service by setting up a [user-provided service](stages.md#ups)
for an existing instance of your service. That will let you validate
the integration design before you make a large development investment,
and it will let real consumers weigh in development priorities.

A critical component to this step is the development of consuming
applications. Those can be real customer applications, or test applications
that are deployed to PCF.

- [Developing applications](app-development.md)
- [Binding services](service-binding.md)

## Step 5. Develop your components

Once the design is established and validated, and the first [stage](stages.md)
has been defined, you would start actual development of your tile.

## Step 6. Maintain your tile

- [Set up a Concourse Server](concourse.md#server)
- [Set up a Concourse Pipeline](concourse.md#pipeline)
- [Create a target PCF pool](concourse.md#pool)

- [Upgrading tiles](tile-generator.md#upgrades)
