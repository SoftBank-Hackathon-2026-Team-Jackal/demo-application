#!/usr/bin/env python3
"""Create one CloudFront HTTPS endpoint for the demo ALB origin."""

import argparse
from datetime import datetime, timezone
import json

import boto3


COMMENT = "cmp-demo-source-api"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True, help="ALB DNS name without scheme")
    parser.add_argument("--profile", default="cmp-aws-prod")
    args = parser.parse_args()
    if "/" in args.origin or ":" in args.origin:
        parser.error("origin must be a bare DNS name")

    client = boto3.Session(profile_name=args.profile).client("cloudfront")
    paginator = client.get_paginator("list_distributions")
    for page in paginator.paginate():
        for distribution in page.get("DistributionList", {}).get("Items", []):
            if distribution.get("Comment") == COMMENT:
                current = distribution["Origins"]["Items"][0]["DomainName"]
                if current != args.origin:
                    parser.error(f"existing distribution uses a different origin: {current}")
                print(json.dumps({"id": distribution["Id"], "url": f"https://{distribution['DomainName']}", "status": distribution["Status"]}))
                return

    config = {
        "CallerReference": f"cmp-demo-source-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "Comment": COMMENT,
        "Enabled": True,
        "Origins": {
            "Quantity": 1,
            "Items": [{
                "Id": "demo-source-alb",
                "DomainName": args.origin,
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "http-only",
                    "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
                },
            }],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "demo-source-alb",
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {
                "Quantity": 7,
                "Items": ["GET", "HEAD", "OPTIONS", "PUT", "PATCH", "POST", "DELETE"],
                "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
            },
            "ForwardedValues": {
                "QueryString": True,
                "Cookies": {"Forward": "none"},
                "Headers": {"Quantity": 2, "Items": ["X-Demo-Write-Token", "Content-Type"]},
            },
            "MinTTL": 0,
            "DefaultTTL": 0,
            "MaxTTL": 0,
            "Compress": True,
        },
        "PriceClass": "PriceClass_All",
        "ViewerCertificate": {"CloudFrontDefaultCertificate": True},
        "Restrictions": {"GeoRestriction": {"RestrictionType": "none", "Quantity": 0}},
        "HttpVersion": "http2",
        "IsIPV6Enabled": True,
    }
    result = client.create_distribution(DistributionConfig=config)["Distribution"]
    print(json.dumps({"id": result["Id"], "url": f"https://{result['DomainName']}", "status": result["Status"]}))


if __name__ == "__main__":
    main()
