#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { WorkshopStack } from "../lib/workshop-stack";

const app = new cdk.App();
const projectName = app.node.tryGetContext("projectName") ?? "agentic-rag-workshop";

new WorkshopStack(app, "AgenticRagWorkshopStack", {
  projectName,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
  },
});
