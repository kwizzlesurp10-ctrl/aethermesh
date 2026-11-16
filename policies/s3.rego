package aethermesh.s3

import rego.v1

deny contains msg if {
    input.proposedChange.module == "modules/s3-static-bucket"
    not input.proposedChange.public_access_block
    msg := "public_access_block must be true"
}

deny contains msg if {
    input.proposedChange.module == "modules/s3-static-bucket"
    input.proposedChange.acl == "public-read"
    msg := "ACL must not be public-read"
}

deny contains msg if {
    input.proposedChange.module == "modules/s3-static-bucket"
    not input.proposedChange.encryption.enabled
    msg := "server-side encryption must be enabled"
}

deny contains msg if {
    input.proposedChange.module == "modules/s3-static-bucket"
    not input.proposedChange.tags["Environment"]
    msg := "tag Environment is required"
}

deny contains msg if {
    input.proposedChange.module == "modules/s3-static-bucket"
    not input.proposedChange.tags["Owner"]
    msg := "tag Owner is required"
}

deny contains msg if {
    input.intent.maxMonthlyCostUSD
    input.proposedChange.estMonthlyCostUSD > input.intent.maxMonthlyCostUSD
    msg := sprintf("estimated cost %v exceeds maxMonthlyCostUSD %v", [
        input.proposedChange.estMonthlyCostUSD,
        input.intent.maxMonthlyCostUSD,
    ])
}
