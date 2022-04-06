# snet-converter-services
[![CircleCI](https://circleci.com/gh/singnet/snet-cli.svg?style=svg)](https://circleci.com/gh/singnet/snet-converter-services)
<br>Backend APIs as Conveter Services


```
Converter Service│   
├── v1
│   │   ├── blockchain 
│   │       ├── GET           ----> (1) 
│   │   ├── token
│   │         ├── pair 
│   │           ├── GET       ----> (2)
│   │   ├── conversion  
│   │       ├── POST          ----> (3)
|   |       |__ GET           ----> (7)  
│   │       ├── history        
│   │       |    ├── POST      ----> (5)
|   |       |__{converion_id}
|   |       |   |__ claim     -----> (6)
|   |       |__ count
|   |            |__ GET      -----> (9)
│   │   ├── transaction  
│   │       ├── POST          ----> (4)
|   |   |__ wallet
|   |       |__ address
|   |          |__ GET        ----> (8)
│   │   └── other-services
```

***
## LIST OF APIs

 1. [Get all blockchain](#1-get-all-blockchain)
 2. [Get all token pair](#2-get-all-token-pair)
 3. [Create conversion request](#3-create-a-conversion-request)
 4. [Create a Transaction for Conversion](#4-create-a-transaction-for-conversion)
 5. [Get Conversion History](#5-get-conversion-history)
 6. [Claim Conversion](#6-claim-conversion)
 7. [Get conversion](#7-get-conversion)
 8. [Get wallets address by ethereum address](#8-get-wallets-address-by-ethereum-address)
 9. [Get conversion count by status](#9--get-conversion-count-by-status)


## LIST OF Internal Lambda

 1. [Cardano Event Consumer](#1-converter-event-consumer)
 2. [Converter Bridge](#2-converter-bridge)
 3. [Get all deposit address](#3-get-all-the-deposit-address)
 4. [Expire conversion](#4-expire-the-conversion)

### 1. Get all blockchain
  API Url: `{DOMAIN_URL}/{STAGE}/v1/blockchain` 

  Method: `GET`

  Request : No headers or params needed

  Response: 

```json5
{
    "status": "success",
    "data": [
        {
            "id": "5b21294fe71a4145a40f6ab918a50f96",
            "name": "Cardano",
            "description": "Add your wallet address",
            "symbol": "ADA",
            "logo": "www.cardano.com/image.png",
            "is_extension_available": false,
            "chain_id": 2,
            "updated_at": "2022-01-12 04: 10: 54"
        },
        {
            "id": "a38b4038c3a04810805fb26056dfabdd",
            "name": "Ethereum",
            "description": "Connect with your wallet",
            "symbol": "ETH",
            "logo": "www.ethereum.com/image.png",
            "is_extension_available": true,
            "chain_id": 42,
            "updated_at": "2022-01-12 04: 10: 54"
        }
    ],
    "error": {
        "code": null,
        "message": null,
        "details": null
    }
}
```


### 2. Get all token pair
  API Url: `{DOMAIN_URL}/{STAGE}/v1/token/pair` 

  Method: `GET`

  Request : No headers or params needed

  Response: 

```json5
{
    "status": "success",
    "data": [
        {
            "id": "22477fd4ea994689a04646cbbaafd133",
            "min_value": "1E+1",
            "max_value": "1E+8",
            "contract_address": "0xacontractaddress",
            "from_token": {
                "id": "53ceafdb42ad4f3d81eeb19c674437f9",
                "symbol": "AGIX",
                "logo": "www.findOurUrl.com/image.png",
                "allowed_decimal": 5,
                "token_address": "0xA1e841e8F770E5c9507E2f8cfd0aA6f73009715d",
                "updated_at": "2022-01-12 04:10:54",
                "blockchain": {
                    "id": "a38b4038c3a04810805fb26056dfabdd",
                    "name": "Ethereum",
                    "symbol": "ETH",
                    "chain_id": 42
                }
            },
            "to_token": {
                "id": "aa5763de861e4a52ab24464790a5c017",
                "symbol": "AGIX",
                "logo": "www.findOurUrl.com/image.png",
                "allowed_decimal": 10,
                "token_address": "ae8a0b54484418a3db56f4e9b472d51cbc860667489366ba6e150c8a",
                "updated_at": "2022-01-12 04:10:54",
                "blockchain": {
                    "id": "5b21294fe71a4145a40f6ab918a50f96",
                    "name": "Cardano",
                    "symbol": "ADA",
                    "chain_id": 2
                }
            },
            "conversion_fee": {
                "id": "ccd10383bd434bd7b1690754f8b98df3",
                "percentage_from_source": "1.5",
                "updated_at": "2022-01-12 04:10:54"
            },
            "updated_at": "2022-01-12 04:10:54"
        },
        {
            "id": "fdd6a416d8414154bcdd95f82b6ab239",
            "min_value": "1E+2",
            "max_value": "1E+9",
            "contract_address": "0xacontractaddress",
            "from_token": {
                "id": "aa5763de861e4a52ab24464790a5c017",
                "symbol": "AGIX",
                "logo": "www.findOurUrl.com/image.png",
                "allowed_decimal": 10,
                "updated_at": "2022-01-12 04:10:54",
                "token_address": "ae8a0b54484418a3db56f4e9b472d51cbc860667489366ba6e150c8a",
                "blockchain": {
                    "id": "5b21294fe71a4145a40f6ab918a50f96",
                    "name": "Cardano",
                    "symbol": "ADA",
                    "chain_id": 2
                }
            },
            "to_token": {
                "id": "53ceafdb42ad4f3d81eeb19c674437f9",
                "symbol": "AGIX",
                "logo": "www.findOurUrl.com/image.png",
                "allowed_decimal": 5,
                "updated_at": "2022-01-12 04:10:54",
                "token_address": "0xA1e841e8F770E5c9507E2f8cfd0aA6f73009715d",
                "blockchain": {
                    "id": "a38b4038c3a04810805fb26056dfabdd",
                    "name": "Ethereum",
                    "symbol": "ETH",
                    "chain_id": 42
                }
            },
            "conversion_fee": {},
            "updated_at": "2022-01-12 04:10:54"
        }
    ],
    "error": {
        "code": null,
        "message": null,
        "details": null
    }
}
```

### 3. Create a conversion request
  API Url: `{DOMAIN_URL}/{STAGE}/v1/conversion` 

  Method: `POST`

  Request :

```json5
{
  "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
  "amount": "1333.05",
  "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
  "to_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
  "block_number": 12345678,
  "signature": "0xd4159d88ccc844ced5f0fa19b2975877813ab82f5c260d8cbacc1c11e9d61e8c776db78473a052ee02da961e98c7326f70c5e37e9caa2240dbb17baea2d4c69c1b"
}
```

  Response: 

`signature` will be available only for ethereum conversion on `FROM` side
`deposit_address` will be available only for cardano conversion on `FROM` side

```json5
{
  "status": "success",
  "data": {
    "id": "02bdcb4e65d1491586110cbf4a16efe8",
    "amount": "1.33305E+8",
    "deposit_address": null,
    "signature": "0x0faa47c8744ec7c8dfbccb95010e1b8a4aeeaad43f0d3452cccdf78b8798200264598f3540cb0fea150e4d748d102a3799c77555d658bb641a7c087a02fdaefa1b",
    "contract_address": "some contract address"
  },
  "error": {
    "code": null,
    "message": null,
    "details": null
  }
}
```

### 4. Create a Transaction for Conversion
  API Url: `{DOMAIN_URL}/{STAGE}/v1/transaction` 

  Method: `POST`

  Request :

```json5
{
  "conversion_id": "07e17d5165a74a79a8d4caa4a640caba",
  "transaction_hash": "22477fd4ea994689a04646cbbaafd133"
}
```

  Response: 
```json5
{
  "status": "success",
  "data": {
    "id": "e5c2a10ebe4e4a588ddb68c31a784ffa"
  },
  "error": {
    "code": null,
    "message": null,
    "details": null
  }
}
```

### 5. Get Conversion History
  API Url: `{DOMAIN_URL}/{STAGE}/v1/conversion/history` 

  Method: `GET`

  Request :

```json5
{
  "queryStringParameters":{
    "address" : "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
    "page_size":15,
    "page_number": 1
  }
}
```

  Response: 
```json5
{
        "status": "success",
        "data": {
            "items": [
                {
                    "conversion": {
                        "id": "1ad29ed5cd8d49eeb08d571bc63acfaf",
                        "deposit_amount": "1E+6",
                        "claim_amount": "1E+6",
                        "fee_amount": "0",
                        "status": "WAITING_FOR_CLAIM",
                        "created_at": "2022-03-23 16:36:34",
                        "updated_at": "2022-03-23 16:43:35"
                    },
                    "wallet_pair": {
                        "from_address": "addr_test1qquj76vq3q4wut49m43dgxa8839uc0llepyyuyn3kjy7fn3kyuuqxnr3wlf2dgts9djqkju4ycn06vjmyj035eyfufxsmq9mn5",
                        "to_address": "0x176133a958449C28930970989dB5fFFbEdd9F447",
                        "deposit_address": "addr_test1vr35awvktjyv7mfq7advku5p8wmjcrn05tqar7p5fzpp7gq8w70e3"
                    },
                    "from_token": {
                        "name": "Singularity NTX Cardano",
                        "symbol": "NTX",
                        "allowed_decimal": 6,
                        "blockchain": {
                            "name": "Cardano",
                            "symbol": "ADA",
                            "chain_id": 2
                        }
                    },
                    "to_token": {
                        "name": "Singularity NTX Ethereum",
                        "symbol": "NTX",
                        "allowed_decimal": 6,
                        "blockchain": {
                            "name": "Ethereum",
                            "symbol": "ETH",
                            "chain_id": 3
                        }
                    },
                    "transactions": [
                        {
                            "id": "344d1f4e88c0415c8a8d2ec464cde36c",
                            "transaction_operation": "TOKEN_RECEIVED",
                            "transaction_hash": "93087d747871642b883b6343f74c5e32678daf1611df7f70bcd0ba59fe9c4c1d",
                            "transaction_amount": "1E+6",
                            "confirmation": 3,
                            "status": "SUCCESS",
                            "created_at": "2022-03-23 16:41:30",
                            "updated_at": "2022-03-23 16:41:30",
                            "token": {
                                "name": "Singularity NTX Cardano",
                                "symbol": "NTX",
                                "allowed_decimal": 6,
                                "blockchain": {
                                    "name": "Cardano",
                                    "symbol": "ADA",
                                    "chain_id": 2
                                }
                            }
                        },
                        {
                            "id": "3c4c0ab5d7e44b83a6215b52fa685571",
                            "transaction_operation": "TOKEN_BURNT",
                            "transaction_hash": "98c8b3451f30dc5009e711fa4113cfadc6462f8f0a302079a664b891d57e37d8",
                            "transaction_amount": "1E+6",
                            "confirmation": 3,
                            "status": "SUCCESS",
                            "created_at": "2022-03-23 16:41:36",
                            "updated_at": "2022-03-23 16:43:30",
                            "token": {
                                "name": "Singularity NTX Cardano",
                                "symbol": "NTX",
                                "allowed_decimal": 6,
                                "blockchain": {
                                    "name": "Cardano",
                                    "symbol": "ADA",
                                    "chain_id": 2
                                }
                            }
                        }
                    ]
                },
                {
                    "conversion": {
                        "id": "4ed138cd461041ea8554885f0ac9f9c0",
                        "deposit_amount": "1E+8",
                        "claim_amount": "1E+8",
                        "fee_amount": "0",
                        "status": "USER_INITIATED",
                        "created_at": "2022-03-23 20:45:37",
                        "updated_at": "2022-03-23 20:45:37"
                    },
                    "wallet_pair": {
                        "from_address": "0x176133a958449C28930970989dB5fFFbEdd9F447",
                        "to_address": "addr_test1qquj76vq3q4wut49m43dgxa8839uc0llepyyuyn3kjy7fn3kyuuqxnr3wlf2dgts9djqkju4ycn06vjmyj035eyfufxsmq9mn5",
                        "deposit_address": null
                    },
                    "from_token": {
                        "name": "Singularity AGIX Ethereum",
                        "symbol": "AGIX",
                        "allowed_decimal": 8,
                        "blockchain": {
                            "name": "Ethereum",
                            "symbol": "ETH",
                            "chain_id": 3
                        }
                    },
                    "to_token": {
                        "name": "Singularity AGIX Cardano",
                        "symbol": "AGIX",
                        "allowed_decimal": 8,
                        "blockchain": {
                            "name": "Cardano",
                            "symbol": "ADA",
                            "chain_id": 2
                        }
                    },
                    "transactions": []
                }
            ],
            "meta": {
                "total_records": 83,
                "page_count": 42,
                "page_number": 1,
                "page_size": 2
            }
        },
        "error": {
            "code": null,
            "message": null,
            "details": null
        }
}
```

### 6. Claim conversion
  API Url: `{DOMAIN_URL}/{STAGE}/v1/conversion/{conversion_id}/claim` 

  Method: `POST`
 
  PathParameter:
    Required `conversion_id`

  Request Body :

```json5
{
  "amount": "1000",
  "from_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
  "to_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
  "signature": "0x3b8421d9795dc5a9fd3f46ca109b603367033d7bab882c67c09d60e6b3dd4eec6b3e7a19bd1ce92f9fcba23f33d263fff3e850ac5bbeb24b029fbca9ae6786731b"
}
```

    Response:
```json5
{
  "claim_amount": "1000",
  "signature": "0x3b8421d9795dc5a9fd3f46ca109b603367033d7bab882c67c09d60e6b3dd4eec6b3e7a19bd1ce92f9fcba23f33d263fff3e850ac5bbeb24b029fbca9ae6786731b0x3b8421d9795dc5a9fd3f46ca109b603367033d7bab882c67c09d60e6b3dd4eec6b3e7a19bd1ce92f9fcba23f33d263fff3e850ac5bbeb24b029fbca9ae6786731b",
  "contract_address": "some contract address"
}
```

### 7. Get conversion
  API Url: `{DOMAIN_URL}/{STAGE}/v1/conversion/{conversion_id}` 

  Method: `POST`
 
  PathParameter:
    Required `conversion_id`

  Response:
```json5
{
    "status": "success",
    "data": {
        "conversion": {
            "id": "1ad29ed5cd8d49eeb08d571bc63acfaf",
            "deposit_amount": "1E+6",
            "claim_amount": "1E+6",
            "fee_amount": "0",
            "status": "WAITING_FOR_CLAIM",
            "created_at": "2022-03-23 16:36:34",
            "updated_at": "2022-03-23 16:43:35"
        },
        "wallet_pair": {
            "from_address": "addr_test1qquj76vq3q4wut49m43dgxa8839uc0llepyyuyn3kjy7fn3kyuuqxnr3wlf2dgts9djqkju4ycn06vjmyj035eyfufxsmq9mn5",
            "to_address": "0x176133a958449C28930970989dB5fFFbEdd9F447",
            "deposit_address": "addr_test1vr35awvktjyv7mfq7advku5p8wmjcrn05tqar7p5fzpp7gq8w70e3"
        },
        "from_token": {
            "name": "Singularity NTX Cardano",
            "symbol": "NTX",
            "allowed_decimal": 6,
            "blockchain": {
                "name": "Cardano",
                "symbol": "ADA",
                "chain_id": 2
            }
        },
        "to_token": {
            "name": "Singularity NTX Ethereum",
            "symbol": "NTX",
            "allowed_decimal": 6,
            "blockchain": {
                "name": "Ethereum",
                "symbol": "ETH",
                "chain_id": 3
            }
        },
        "transactions": [
            {
                "id": "344d1f4e88c0415c8a8d2ec464cde36c",
                "transaction_operation": "TOKEN_RECEIVED",
                "transaction_hash": "93087d747871642b883b6343f74c5e32678daf1611df7f70bcd0ba59fe9c4c1d",
                "transaction_amount": "1E+6",
                "confirmation": 3,
                "status": "SUCCESS",
                "created_at": "2022-03-23 16:41:30",
                "updated_at": "2022-03-23 16:41:30",
                "token": {
                    "name": "Singularity NTX Cardano",
                    "symbol": "NTX",
                    "allowed_decimal": 6,
                    "blockchain": {
                        "name": "Cardano",
                        "symbol": "ADA",
                        "chain_id": 2
                    }
                }
            },
            {
                "id": "3c4c0ab5d7e44b83a6215b52fa685571",
                "transaction_operation": "TOKEN_BURNT",
                "transaction_hash": "98c8b3451f30dc5009e711fa4113cfadc6462f8f0a302079a664b891d57e37d8",
                "transaction_amount": "1E+6",
                "confirmation": 3,
                "status": "SUCCESS",
                "created_at": "2022-03-23 16:41:36",
                "updated_at": "2022-03-23 16:43:30",
                "token": {
                    "name": "Singularity NTX Cardano",
                    "symbol": "NTX",
                    "allowed_decimal": 6,
                    "blockchain": {
                        "name": "Cardano",
                        "symbol": "ADA",
                        "chain_id": 2
                    }
                }
            }
        ]
    },
    "error": {
        "code": null,
        "message": null,
        "details": null
    }
}
```

### 8. Get wallets address by ethereum address

  API Url: `{DOMAIN_URL}/{STAGE}/v1/wallet/address?ethereum_address={ethereum_address}` 

  Method: `POST`
 
  Query String Parameter:
    Required `ethereum_address`

  Response:
```json5
{
    "status": "success",
    "data": {
        "cardano_address": "addr_test1qq02e0v7zhl8xveugy6xjdml6qxkh9fxeh9860yew2ld3nv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8q6s4gt5"
    },
    "error": {
        "code": null,
        "message": null,
        "details": null
    }
}
```

### 9 . Get conversion count by status

  API Url: `{DOMAIN_URL}/{STAGE}/v1/conversion/count?address={ethereum_address}` 

  Method: `GET`
 
  Query String Parameter:
    Required `address`

  Response:
```json5
{
	"status": "success",
	"data": {
		"overall_count": 141,
		"each": {
			"SUCCESS": 99,
			"PROCESSING": 20,
			"USER_INITIATED": 10,
			"CLAIM_INITIATED": 2,
			"WAITING_FOR_CLAIM": 5,
			"EXPIRED": 5
		}
	},
	"error": {
		"code": null,
		"message": null,
		"details": null
	}
}
```


###Internal Lambda

### 1. Converter Event Consumer
  
SQS Subscribed to events, sample format

```json5
{
    "Records": [
        {
            "messageId": "08bffcaa-2024-4b6e-89af-5fa33f960e3a",
            "receiptHandle": "AQEBVZtwum2uv9OYAhcudGTNqLvzBSJkty2Nxx9j4zoBHDuHBWlZGkJBVLp92S6ZsmreElQzPcVF9PhQQspPQtwq55ZPbU9HFJhFrnUtSILEv+UFdlQDUfqr/zbgWUpqhywfYy37aKTHYd+Ega82p190b+2+aZTZlhwxN201oemVQ935ZzjdSfoQg/Obg66+1zuINRYj6SCtXbVE+XDTzKtxsEXAr93psUk+n/rXZNatAAFEcTTJJLa61g9pIjuij2deiHFAiAVHrAhZLRM31jD8O0j/0Pplm+7VdGYOLrlErkniTcRj/kX4agCjdD8H1pcwOzJJvUJoA67FZTzvzPMFUVmf6Pz+5vEMr8PEIGodAlRYDp7mMo9bPbAcpFjqv4RH",
            "body": "{\n  \"Type\" : \"Notification\",\n  \"MessageId\" : \"855599be-7423-5355-8a5d-c336fd21849d\",\n  \"TopicArn\" : \":12345678:rt-sns2\",\n  \"Subject\" : \"hi\",\n  \"Message\" : \"{\\\"id\\\": \\\"358e6b97ece44dc1b20f1949135db3c1\\\", \\\"tx_hash\\\": \\\"9aae782f0118f5878bda5f8f89dd41619475a3e797253fde41e6e4413f5e302c\\\", \\\"event_type\\\": \\\"TOKEN_BURNED\\\", \\\"address\\\": null, \\\"event_status\\\": null, \\\"updated_at\\\": \\\"2022-02-05 04:16:38\\\", \\\"asset\\\": {\\\"id\\\": \\\"2b1ad0cb84464a99b0e3fd30b1f39d15\\\", \\\"asset\\\": \\\"34d1adbf3a7e95b253fd0999fb85e2d41d4121b36b834b83ac069ebb41474958\\\", \\\"policy_id\\\": \\\"34d1adbf3a7e95b253fd0999fb85e2d41d4121b36b834b83ac069ebb\\\", \\\"asset_name\\\": \\\"41474958\\\", \\\"allowed_decimal\\\": 8, \\\"updated_at\\\": \\\"2022-02-05 04:01:28\\\"}, \\\"transaction_detail\\\": {\\\"id\\\": \\\"ef33fa2069e74fd0885c042f61376a08\\\", \\\"tx_type\\\": \\\"TOKEN_BURNED\\\", \\\"assurance_level\\\": \\\"HIGH\\\", \\\"confirmations\\\": 167492, \\\"tx_amount\\\": \\\"-3E+8\\\", \\\"tx_fee\\\": \\\"1E+6\\\", \\\"block_number\\\": 3131167, \\\"block_time\\\": 1638790693, \\\"tx_metadata\\\": {}, \\\"updated_at\\\": \\\"2022-02-06 17:43:03\\\"}}\\n\",\n  \"Timestamp\" : \"2022-02-17T17:32:50.084Z\",\n  \"SignatureVersion\" : \"1\",\n  \"Signature\" : \"IfHeTjg+ynU5bM6IgtOgdPpUYwi9rqtGqIX4bfscyuUFNkAB51jzoUC80xLcedA0Ma1IGhH+P78Cg2i/9s95tMUUprBc5Z5EKx49HIAJMpWgJuhqom24Fl2WX4ib2D4271vRPBFQV7oyo7c6dnF9mzgNVSC5yl5EjbWBH8VHpYw0uWxyih5w0hBJIOe2x1q/sx5hqyy5Dh77DS9Yter1nncewa2dQIFIBF5qnkMEDNjKTg7K3TfvfzliEW0SrEk8Zg5e7BCgpRC6FYqhJvw6In7o31mInTgCEMXNnh2lOJ21uH5Yi7kVbWvBYuAbPey4PDdfqjk1QDB+pMXgPqRR7g==\",\n  \"SigningCertURL\" : \"https://sns.us-east-1.amazonaws.com/SimpleNotificationService-7ff5318490ec183fbaddaa2a969abfda.pem\",\n  \"UnsubscribeURL\" : \"https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=:12345678:rt-sns2:25edd3be-e87c-4ea7-ba3b-ff52001cfd89\"\n}",
            "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1645119170125",
                "SenderId": "AIDAIT2UOQQY3AUEKVGXU",
                "ApproximateFirstReceiveTimestamp": "1645119170135"
            },
            "messageAttributes": {},
            "md5OfBody": "39d217f12c2a8aa92ab9e6c6d7d83a7d",
            "eventSource": "aws:sqs",
            "eventSourceARN": ":12345678:rt-sqs1",
            "awsRegion": "us-east-1"
        }
    ]
}
```



### 2. Converter Bridge

Another sample  payload 

```json5
{
    "Records": [
        {
            "messageId": "e816ede8-7c3a-4720-8d4e-1c6db3dd42ad",
            "receiptHandle": "AQEBTI12SRQlGn7QXD+E9Xgq0sELFTFYZOtKsNuKLr1vqS+Q8uvsdiVZc1vhzKwi7G6GQGvHBN9HLwndLIsADt+us0YqfLQE9X/JrStdWdCsxHKsdLLNVtzwMeRTZkWiJJcl1jSycAyrpsc712jkhiIF4LNe4bYmXOWngEWyAbRmnxwe0g5/oGMNsTnkI+FizvvCTLzOQljbgFlMIAZh0tDmOy/4si62niVDePqspzl51v3KiSAabeH/neUI3aO8wX+cXTdgui99gyb3eYTAEPhzjm4lM6mXhls4i1l+R6W2onRh7feUYxCsAaeXuz43LRBI+6kTERg2Qgj0PM8gSsaSYIYWb8td/vBK+vidM81VgKK1+tdrh0VkE9gGAFJ7Otjo",
            "body": "{\"blockchain_name\": \"Ethereum\", \"blockchain_event\": {\"conversion_id\": \"c94add99a9a24a18816ed505771c4090\", \"tx_amount\": \"1E+8\", \"tx_operation\": \"TOKEN_UNLOCKED\"}, \"blockchain_network_id\": 42}\n",
            "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1645122763537",
                "SenderId": "AROAXWVWLXRYFHMBAM2KS:Karthikeyan.Balusamy@breville.com",
                "ApproximateFirstReceiveTimestamp": "1645122763538"
            },
            "messageAttributes": {},
            "md5OfBody": "664d3f0e820b2561cd2c5ce111957e08",
            "eventSource": "aws:sqs",
            "eventSourceARN": ":12345678:rt-sqs1",
            "awsRegion": "us-east-1"
        }
    ]
}
```
### 3. Get all the deposit address

    Request: `None`
    
    Response:
```json5
{
    "status": "success",
    "data": {
        "addresses": [
            "addr_test1vpmh8nfmj353v80ehdn9dh0dyln70x7vs68jvf7rl6wxglsyjck38"
        ]
    },
    "error": {
        "code": null,
        "message": null,
        "details": null
    }
}
```

### 4. Expire the conversion

we are expiring the conversion based on the configuration set