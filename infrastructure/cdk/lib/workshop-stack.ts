import * as path from "path";
import {
  Stack,
  StackProps,
  CfnOutput,
  RemovalPolicy,
  Duration,
  CustomResource,
  Tags,
} from "aws-cdk-lib";
import { Construct } from "constructs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as cr from "aws-cdk-lib/custom-resources";
import * as opensearchserverless from "aws-cdk-lib/aws-opensearchserverless";

export interface WorkshopStackProps extends StackProps {
  projectName: string;
}

export class WorkshopStack extends Stack {
  constructor(scope: Construct, id: string, props: WorkshopStackProps) {
    super(scope, id, props);

    const { projectName } = props;

    // ── S3 Bucket ──
    const bucket = new s3.Bucket(this, "DocumentBucket", {
      bucketName: `${projectName}-documents-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
    Tags.of(bucket).add("Project", projectName);

    // ── IAM Roles (created before AOSS policies so ARNs are available) ──
    const kbRole = new iam.Role(this, "KnowledgeBaseRole", {
      roleName: `${projectName}-kb-role`,
      assumedBy: new iam.ServicePrincipal("bedrock.amazonaws.com"),
    });

    const lambdaRole = new iam.Role(this, "LambdaRole", {
      roleName: `${projectName}-lambda-role`,
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        ),
      ],
    });

    // KB Role policies
    kbRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["s3:GetObject", "s3:ListBucket"],
        resources: [bucket.bucketArn, `${bucket.bucketArn}/*`],
      })
    );
    kbRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          `arn:aws:bedrock:${this.region}::foundation-model/amazon.titan-embed-text-v2:0`,
          `arn:aws:bedrock:${this.region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0`,
        ],
      })
    );
    kbRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["aoss:APIAccessAll"],
        resources: [`arn:aws:aoss:${this.region}:${this.account}:collection/*`],
      })
    );
    kbRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["lambda:InvokeFunction"],
        resources: [
          `arn:aws:lambda:${this.region}:${this.account}:function:workshop-custom-chunker`,
        ],
      })
    );

    // Lambda Role policies
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        resources: [bucket.bucketArn, `${bucket.bucketArn}/*`],
      })
    );
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock:InvokeModel",
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate",
        ],
        resources: ["*"],
      })
    );
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock-agent:*"],
        resources: ["*"],
      })
    );
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["aoss:APIAccessAll"],
        resources: [`arn:aws:aoss:${this.region}:${this.account}:collection/*`],
      })
    );
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["neptune-graph:*"],
        resources: ["*"],
      })
    );

    // ── OpenSearch Serverless ──
    const encryptionPolicy =
      new opensearchserverless.CfnSecurityPolicy(this, "EncryptionPolicy", {
        name: `${projectName}-enc`,
        type: "encryption",
        policy: JSON.stringify({
          Rules: [
            {
              ResourceType: "collection",
              Resource: [`collection/${projectName}`],
            },
          ],
          AWSOwnedKey: true,
        }),
      });

    const networkPolicy =
      new opensearchserverless.CfnSecurityPolicy(this, "NetworkPolicy", {
        name: `${projectName}-net`,
        type: "network",
        policy: JSON.stringify([
          {
            Rules: [
              {
                ResourceType: "collection",
                Resource: [`collection/${projectName}`],
              },
              {
                ResourceType: "dashboard",
                Resource: [`collection/${projectName}`],
              },
            ],
            AllowFromPublic: true,
          },
        ]),
      });

    const dataAccessPolicy =
      new opensearchserverless.CfnAccessPolicy(this, "DataAccessPolicy", {
        name: `${projectName}-access`,
        type: "data",
        policy: JSON.stringify([
          {
            Rules: [
              {
                ResourceType: "collection",
                Resource: [`collection/${projectName}`],
                Permission: [
                  "aoss:CreateCollectionItems",
                  "aoss:UpdateCollectionItems",
                  "aoss:DescribeCollectionItems",
                ],
              },
              {
                ResourceType: "index",
                Resource: [`index/${projectName}/*`],
                Permission: [
                  "aoss:CreateIndex",
                  "aoss:UpdateIndex",
                  "aoss:DescribeIndex",
                  "aoss:ReadDocument",
                  "aoss:WriteDocument",
                ],
              },
            ],
            Principal: [kbRole.roleArn, lambdaRole.roleArn],
          },
        ]),
      });

    const collection = new opensearchserverless.CfnCollection(
      this,
      "Collection",
      {
        name: projectName,
        type: "VECTORSEARCH",
        description: "Vector store for Bedrock Knowledge Base",
      }
    );
    collection.addDependency(encryptionPolicy);
    collection.addDependency(networkPolicy);
    collection.addDependency(dataAccessPolicy);
    Tags.of(collection).add("Project", projectName);

    // ── Custom Resource: Create OpenSearch Index ──
    const createIndexFn = new lambda.Function(this, "CreateIndexFunction", {
      functionName: `${projectName}-create-index`,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "..", "lambda", "create-index")
      ),
      role: lambdaRole,
      timeout: Duration.seconds(120),
      memorySize: 256,
      environment: {
        COLLECTION_ENDPOINT: collection.attrCollectionEndpoint,
        INDEX_NAME: "workshop-kb-index",
      },
    });

    const provider = new cr.Provider(this, "CreateIndexProvider", {
      onEventHandler: createIndexFn,
    });

    new CustomResource(this, "CreateIndexResource", {
      serviceToken: provider.serviceToken,
    });

    // ── Outputs ──
    new CfnOutput(this, "WorkshopBucket", {
      value: bucket.bucketName,
      exportName: `${projectName}-bucket`,
    });
    new CfnOutput(this, "OpenSearchCollectionArn", {
      value: collection.attrArn,
      exportName: `${projectName}-collection-arn`,
    });
    new CfnOutput(this, "OpenSearchCollectionEndpoint", {
      value: collection.attrCollectionEndpoint,
      exportName: `${projectName}-collection-endpoint`,
    });
    new CfnOutput(this, "KnowledgeBaseRoleArn", {
      value: kbRole.roleArn,
      exportName: `${projectName}-kb-role-arn`,
    });
    new CfnOutput(this, "LambdaRoleArn", {
      value: lambdaRole.roleArn,
      exportName: `${projectName}-lambda-role-arn`,
    });
  }
}
