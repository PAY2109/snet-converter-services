import json
import unittest
from decimal import Decimal
from unittest.mock import patch, Mock

from sqlalchemy import distinct

from application.handler.conversion_handlers import create_conversion_request, get_conversion_history, \
    create_transaction_for_conversion, claim_conversion, get_conversion, get_conversion_count_by_status, \
    expire_conversion, get_transaction_by_conversion_id
from constants.error_details import ErrorCode, ErrorDetails
from constants.lambdas import LambdaResponseStatus
from constants.status import ConversionStatus
from infrastructure.models import TokenPairDBModel, ConversionFeeDBModel, TokenDBModel, BlockChainDBModel, \
    WalletPairDBModel, ConversionDBModel, TransactionDBModel, ConversionTransactionDBModel, MessageGroupPoolDBModel
from infrastructure.repositories.conversion_repository import ConversionRepository
from testcases.functional_testcases.test_variables import TestVariables
from utils.exceptions import BadRequestException, InternalServerErrorException

conversion_repo = ConversionRepository()


class TestConversion(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        TestConversion.delete_all_tables()

    def setUp(self):
        conversion_repo.session.add_all(TestVariables().blockchain)
        conversion_repo.session.commit()
        conversion_repo.session.add_all(TestVariables().token)
        conversion_repo.session.commit()
        conversion_repo.session.add_all(TestVariables().conversion_fee)
        conversion_repo.session.commit()
        conversion_repo.session.add_all(TestVariables().token_pair)
        conversion_repo.session.commit()
        conversion_repo.session.add_all(TestVariables().wallet_pair)
        conversion_repo.session.commit()
        conversion_repo.session.add_all(TestVariables().conversion)
        conversion_repo.session.commit()
        conversion_repo.session.add_all(TestVariables().conversion_transaction)
        conversion_repo.session.commit()
        conversion_repo.session.add_all(TestVariables().transaction)
        conversion_repo.session.commit()

    @patch("common.blockchain_util.BlockChainUtil.get_current_block_no")
    @patch("application.service.cardano_service.CardanoService.get_deposit_address",
           Mock(return_value={"data": {"derived_address": "some derived address", "index": 1, "role": 0}}))
    @patch("application.service.conversion_service.get_signature")
    @patch("utils.blockchain.validate_cardano_address")
    @patch("common.utils.Utils.report_slack")
    def test_create_conversion_request(self, mock_report_slack, mock_validate_cardano_address, mock_signature,
                                       mock_get_current_block_no):
        mock_signature.return_value = "some signature"

        conversion_repo.session.query(TransactionDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(ConversionTransactionDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(ConversionDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(WalletPairDBModel).delete()
        conversion_repo.session.commit()

        bad_request_body_missing = {'status': 'failed', 'data': None,
                                    'error': {'code': 'E0001', 'message': 'BAD_REQUEST', 'details': 'Missing body'}}
        bad_request_schema_not_matching = {'status': 'failed', 'data': None,
                                           'error': {'code': 'E0003', 'message': 'BAD_REQUEST',
                                                     'details': 'Schema is not matching with request'}}
        bad_request_property_value_empty = {'status': 'failed', 'data': None,
                                            'error': {'code': 'E0005', 'message': 'BAD_REQUEST',
                                                      'details': 'Property value is empty'}}
        bad_request_token_pair_id_not_exists = {'status': 'failed', 'data': None,
                                                'error': {'code': 'E0071', 'message': 'BAD_REQUEST',
                                                          'details': 'Token pair not exists'}}
        bad_request_incorrect_signature = {'status': 'failed', 'data': None,
                                           'error': {'code': 'E0006', 'message': 'BAD_REQUEST',
                                                     'details': 'Incorrect signature provided'}}
        bad_request_invalid_cardano_address = {'status': 'failed', 'data': None,
                                               'error': {'code': 'E0016', 'message': 'BAD_REQUEST',
                                                         'details': 'Invalid address for this network or malformed '
                                                                    'address format.'}}
        unexpected_error_cardano_address_validation = {'status': 'failed', 'data': None,
                                                       'error': {'code': 'E0017', 'message': 'INTERNAL_SERVER_ERROR',
                                                                 'details': 'Unexpected error occurred during address '
                                                                            'validation'}}
        bad_request_amount_should_be_greater_than_zero = {'data': None,
                                                          'error': {'code': 'E0063',
                                                                    'details': 'Conversion amount must be greater tha zero',
                                                                    'message': 'BAD_REQUEST'},
                                                          'status': 'failed'}
        bad_request_invalid_conversion_amount = {'status': 'failed', 'data': None,
                                                 'error': {'code': 'E0065', 'message': 'BAD_REQUEST',
                                                           'details': 'Invalid conversion amount provided'}}

        bad_request_min_value = {'status': 'failed', 'data': None, 'error': {'code': 'E0061', 'message': 'BAD_REQUEST',
                                                                             'details': 'Amount is less than expected min value '}}
        bad_request_max_value = {'status': 'failed', 'data': None, 'error': {'code': 'E0062', 'message': 'BAD_REQUEST',
                                                                             'details': 'Amount is greater than expected max value'}}
        bad_request_signature_expired = {'status': 'failed', 'data': None,
                                         'error': {'code': 'E0070', 'message': 'BAD_REQUEST',
                                                   'details': 'Signature expired for the given request'}}

        # Bad Request
        event = dict()
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_body_missing)

        body_input = json.dumps({})
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        body_input = json.dumps({
            "token_pair_id": "",
            "amount": "",
            "from_address": "",
            "to_address": "",
            "block_number": ""
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        body_input = json.dumps({
            "token_pair_id": "",
            "amount": "",
            "from_address": "",
            "to_address": "",
            "block_number": 0,
            "signature": ""
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_property_value_empty)

        body_input = json.dumps({
            "token_pair_id": "33477fd4ea994689a04646cbbaafd133",
            "amount": "1333.05",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
            "block_number": 12345678,
            "signature": "0xd4159d88ccc844ced5f0fa19b2975877813ab82f5c260d8cbacc1c11e9d61e8c776db78473a052ee02da961e98c7326f70c5e37e9caa2240dbb17baea2d4c69c1b"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_token_pair_id_not_exists)

        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "1333.05",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
            "block_number": 123456789,
            "signature": "0xd4159d88ccc844ced5f0fa19b2975877813ab82f5c260d8cbacc1c11e9d61e8c776db78473a052ee02da961e98c7326f70c5e37e9caa2240dbb17baea2d4c69c1b"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_conversion_amount)

        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "0",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
            "block_number": 123456789,
            "signature": "0xd4159d88ccc844ced5f0fa19b2975877813ab82f5c260d8cbacc1c11e9d61e8c776db78473a052ee02da961e98c7326f70c5e37e9caa2240dbb17baea2d4c69c1b"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_amount_should_be_greater_than_zero)

        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "1",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
            "block_number": 123456789,
            "signature": "0xd4159d88ccc844ced5f0fa19b2975877813ab82f5c260d8cbacc1c11e9d61e8c776db78473a052ee02da961e98c7326f70c5e37e9caa2240dbb17baea2d4c69c1b"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_min_value)

        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "111111111111111111111111111111111111111111",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
            "block_number": 123456789,
            "signature": "0xd4159d88ccc844ced5f0fa19b2975877813ab82f5c260d8cbacc1c11e9d61e8c776db78473a052ee02da961e98c7326f70c5e37e9caa2240dbb17baea2d4c69c1b"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_max_value)

        body_input = json.dumps({
            "token_pair_id": "32477fd4ea994689a04646cbbaafd133",
            "amount": "1333",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
            "block_number": 12345678,
            "signature": "0xd4159d88ccc844ced5f0fa19b2975877813ab82f5c260d8cbacc1c11e9d61e8c776db78473a052ee02da961e98c7326f70c5e37e9caa2240dbb17baea2d4c69c1b"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_token_pair_id_not_exists)

        mock_get_current_block_no.return_value = 1207979
        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "1000",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf",
            "block_number": 12079580,
            "signature": "0x03ef90b2b121e2c651ad1d4b42f9fe38c7e1503bd9d4854640f8d0d5de843f117d38d0b96427750f917e4aa0f4464b9e60853e3cc10e5018f966033ece2719071c"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_signature_expired)

        mock_get_current_block_no.return_value = 12079580
        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "1000",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf",
            "block_number": 12079580,
            "signature": "0x03ef90b2b121e2c651ad1d4b42f9fe38c7e1503bd9d4854640f8d0d5de843f117d38d0b96427750f917e4aa0f4464b9e60853e3cc10e5018f966033ece2719071c"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_incorrect_signature)

        mock_validate_cardano_address.side_effect = BadRequestException(
            error_code=ErrorCode.INVALID_CARDANO_ADDRESS.value,
            error_details=ErrorDetails[ErrorCode.INVALID_CARDANO_ADDRESS.value].value)
        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "100",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf",
            "block_number": 12079580,
            "signature": "0x03ef90b2b121e2c651ad1d4b42f9fe38c7e1503bd9d4854640f8d0d5de843f117d38d0b96427750f917e4aa0f4464b9e60853e3cc10e5018f966033ece2719071c"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_cardano_address)

        mock_validate_cardano_address.side_effect = InternalServerErrorException(
            error_code=ErrorCode.UNEXPECTED_ERROR_CARDANO_ADDRESS_VALIDATION.value,
            error_details=ErrorDetails[
                ErrorCode.UNEXPECTED_ERROR_CARDANO_ADDRESS_VALIDATION.value].value)
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, unexpected_error_cardano_address_validation)

        mock_validate_cardano_address.side_effect = None
        # success request
        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "100",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf",
            "block_number": 12079580,
            "signature": "0x03ef90b2b121e2c651ad1d4b42f9fe38c7e1503bd9d4854640f8d0d5de843f117d38d0b96427750f917e4aa0f4464b9e60853e3cc10e5018f966033ece2719071c"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(len(body["data"]), 5)
        self.assertIsNotNone(body["data"]["id"])
        self.assertIsNotNone(body["data"]["deposit_amount"])
        self.assertIsNotNone(body["data"]["contract_address"])
        self.assertIsNone(body["data"]["deposit_address"])
        previous_request_id = body["data"]["id"]

        conversion = conversion_repo.session.query(ConversionDBModel).filter(
            ConversionDBModel.id == previous_request_id).first()
        last_updated_dt = conversion.updated_at

        body_input = json.dumps({
            "token_pair_id": "22477fd4ea994689a04646cbbaafd133",
            "amount": "100",
            "from_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "to_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf",
            "block_number": 12079580,
            "signature": "0x03ef90b2b121e2c651ad1d4b42f9fe38c7e1503bd9d4854640f8d0d5de843f117d38d0b96427750f917e4aa0f4464b9e60853e3cc10e5018f966033ece2719071c"
        })
        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(len(body["data"]), 5)
        self.assertIsNotNone(body["data"]["id"])
        self.assertIsNotNone(body["data"]["deposit_amount"])
        self.assertIsNotNone(body["data"]["contract_address"])
        self.assertIsNone(body["data"]["deposit_address"])
        self.assertIsNotNone(body["data"]["signature"])
        self.assertNotEqual(body["data"]["id"], previous_request_id)

        conversion = conversion_repo.session.query(ConversionDBModel).filter(
            ConversionDBModel.id == previous_request_id).first()
        current_last_updated_dt = conversion.updated_at
        self.assertEqual(last_updated_dt, current_last_updated_dt)

        # Length of wallet pair table should be one because , the request is from same from and to address
        wallet_pair_count = conversion_repo.session.query(distinct(WalletPairDBModel.id)).all()
        self.assertEqual(len(wallet_pair_count), 1)
        previous_request_id = body["data"]["id"]

        mock_get_current_block_no.return_value = 123456
        body_input = json.dumps({
            "amount": "1000",
            "signature": "0x9ac7b1dbd03fcdd3bd832c8b5e34953d3e49c1aece3d730c1ff92627c2f56cbc4bfa789d43cc2f09346d4dab458ebdd542b9268b103c7a51673f1ba08502baa71c",
            "token_pair_id": "fdd6a416d8414154bcdd95f82b6ab239",
            "block_number": 123456,
            "to_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "from_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf"
        })

        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(len(body["data"]), 5)
        self.assertIsNotNone(body["data"]["id"])
        self.assertIsNotNone(body["data"]["deposit_amount"])
        self.assertIsNotNone(body["data"]["deposit_address"])
        self.assertIsNone(body["data"]["contract_address"])
        self.assertNotEqual(body["data"]["id"], previous_request_id)

        conversion = conversion_repo.session.query(ConversionDBModel).filter(
            ConversionDBModel.id == previous_request_id).first()
        self.assertNotEqual(conversion.status, ConversionStatus.EXPIRED.value)
        previous_request_id = body["data"]["id"]

        mock_get_current_block_no.return_value = 12120255
        body_input = json.dumps({
            "amount": "200000000",
            "signature": "0x14585fcc0de1157cbdd998c4c67fb04d5d4cd2ccac18e641e9dd140fe5ca193b71e1f8e1869b3d5d9b96d28fb239a2f5fae05216083b2aca9fa188479d927dca1b",
            "token_pair_id": "fdd6a416d8414154bcdd95f82b6ab239",
            "block_number": 12120255,
            "to_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "from_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf"
        })

        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(len(body["data"]), 5)
        self.assertIsNotNone(body["data"]["id"])
        self.assertIsNotNone(body["data"]["deposit_amount"])
        self.assertIsNotNone(body["data"]["deposit_address"])
        self.assertIsNone(body["data"]["contract_address"])
        self.assertNotEqual(body["data"]["id"], previous_request_id)

        conversion = conversion_repo.session.query(ConversionDBModel).filter(
            ConversionDBModel.id == previous_request_id).first()
        self.assertEqual(conversion.status, ConversionStatus.EXPIRED.value)
        previous_request_id = body["data"]["id"]

        mock_get_current_block_no.return_value = 123456
        body_input = json.dumps({
            "amount": "1000",
            "signature": "0x9ac7b1dbd03fcdd3bd832c8b5e34953d3e49c1aece3d730c1ff92627c2f56cbc4bfa789d43cc2f09346d4dab458ebdd542b9268b103c7a51673f1ba08502baa71c",
            "token_pair_id": "fdd6a416d8414154bcdd95f82b6ab239",
            "block_number": 123456,
            "to_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "from_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf"
        })

        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(len(body["data"]), 5)
        self.assertIsNotNone(body["data"]["id"])
        self.assertIsNotNone(body["data"]["deposit_amount"])
        self.assertIsNotNone(body["data"]["deposit_address"])
        self.assertIsNone(body["data"]["contract_address"])
        self.assertNotEqual(body["data"]["id"], previous_request_id)

        conversion = conversion_repo.session.query(ConversionDBModel).filter(
            ConversionDBModel.id == previous_request_id).first()
        self.assertEqual(conversion.status, ConversionStatus.EXPIRED.value)
        previous_request_id = body["data"]["id"]

        mock_get_current_block_no.return_value = 123456
        body_input = json.dumps({
            "amount": "1000",
            "signature": "0x9ac7b1dbd03fcdd3bd832c8b5e34953d3e49c1aece3d730c1ff92627c2f56cbc4bfa789d43cc2f09346d4dab458ebdd542b9268b103c7a51673f1ba08502baa71c",
            "token_pair_id": "fdd6a416d8414154bcdd95f82b6ab239",
            "block_number": 123456,
            "to_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "from_address": "addr_test1qpclwzmqsux25kyleun8ujw3x693w6edrxnw0y3et88ehuv0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qgesgnf"
        })

        event["body"] = body_input
        response = create_conversion_request(event, {})
        body = json.loads(response["body"])
        self.assertEqual(len(body["data"]), 5)
        self.assertIsNotNone(body["data"]["id"])
        self.assertIsNotNone(body["data"]["deposit_amount"])
        self.assertIsNotNone(body["data"]["deposit_address"])
        self.assertIsNone(body["data"]["contract_address"])
        self.assertNotEqual(body["data"]["id"], previous_request_id)

        # Length of wallet pair table should be two because , the request is from different from and to address
        wallet_pair_count = conversion_repo.session.query(distinct(WalletPairDBModel.id)).all()
        self.assertEqual(len(wallet_pair_count), 2)

    @patch("common.utils.Utils.report_slack")
    def test_get_conversion_history(self, mock_report_slack):
        bad_request_schema_not_matching = {'status': 'failed', 'data': None,
                                           'error': {'code': 'E0003', 'message': 'BAD_REQUEST',
                                                     'details': 'Schema is not matching with request'}}
        bad_request_property_value_empty = {'status': 'failed', 'data': None,
                                            'error': {'code': 'E0005', 'message': 'BAD_REQUEST',
                                                      'details': 'Property value is empty'}}
        bad_request_page_size_exceeds_limit = {'status': 'failed', 'data': None,
                                               'error': {'code': 'E0072', 'message': 'BAD_REQUEST',
                                                         'details': 'Page size exceeds the max limit'}}
        bad_request_invalid_ethereum_address = {'status': 'failed', 'data': None,
                                                'error': {'code': 'E0059', 'message': 'BAD_REQUEST',
                                                          'details': 'Invalid ethereum address provided'}}
        success_response_with_history = {'status': 'success', 'data': {'items': [{'conversion': {
            'id': '7298bce110974411b260cac758b37ee0', 'deposit_amount': '1.33305E+8', 'claim_amount': '131305425',
            'fee_amount': '1999575', 'status': 'USER_INITIATED', 'created_at': '2022-01-12 04:10:54',
            'updated_at': '2022-01-12 04:10:54'}, 'wallet_pair': {
            'from_address': '0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1',
            'to_address': 'addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8',
            'deposit_address': None}, 'from_token': {'name': 'Singularity Ethereum', 'symbol': 'AGIX',
                                                     'allowed_decimal': 5,
                                                     'blockchain': {'name': 'Ethereum', 'symbol': 'ETH',
                                                                    'chain_id': 42}}, 'to_token': {
            'name': 'Singularity Cardano', 'symbol': 'AGIX', 'allowed_decimal': 10,
            'blockchain': {'name': 'Cardano', 'symbol': 'ADA', 'chain_id': 2}}, 'transactions': []}, {'conversion': {
            'id': '5086b5245cd046a68363d9ca8ed0027e', 'deposit_amount': '1.33305E+18', 'claim_amount': '1.33305E+18',
            'fee_amount': '0', 'status': 'USER_INITIATED', 'created_at': '2022-01-11 04:10:54',
            'updated_at': '2022-01-12 04:10:54'}, 'wallet_pair': {
            'from_address': 'addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8',
            'to_address': '0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1',
            'deposit_address': 'addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8'},
            'from_token': {
                'name': 'Singularity Cardano',
                'symbol': 'AGIX',
                'allowed_decimal': 10,
                'blockchain': {
                    'name': 'Cardano',
                    'symbol': 'ADA',
                    'chain_id': 2}},
            'to_token': {
                'name': 'Singularity Ethereum',
                'symbol': 'AGIX',
                'allowed_decimal': 5,
                'blockchain': {
                    'name': 'Ethereum',
                    'symbol': 'ETH',
                    'chain_id': 42}},
            'transactions': []},
            {'conversion': {
                'id': '51769f201e46446fb61a9c197cb0706b',
                'deposit_amount': '1.66305E+18',
                'claim_amount': '1.638104E+18',
                'fee_amount': '2.4946E+16',
                'status': 'PROCESSING',
                'created_at': '2022-01-10 04:10:54',
                'updated_at': '2022-01-12 04:10:54'},
                'wallet_pair': {
                    'from_address': '0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1',
                    'to_address': 'addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8',
                    'deposit_address': None},
                'from_token': {
                    'name': 'Singularity Ethereum',
                    'symbol': 'AGIX',
                    'allowed_decimal': 5,
                    'blockchain': {'name': 'Ethereum',
                                   'symbol': 'ETH',
                                   'chain_id': 42}},
                'to_token': {
                    'name': 'Singularity Cardano',
                    'symbol': 'AGIX',
                    'allowed_decimal': 10,
                    'blockchain': {'name': 'Cardano',
                                   'symbol': 'ADA',
                                   'chain_id': 2}},
                'transactions': [{
                    'id': '391be6385abf4b608bdd20a44acd6abc',
                    'transaction_operation': 'TOKEN_RECEIVED',
                    'transaction_hash': '22477fd4ea994689a04646cbbaafd133',
                    'transaction_amount': '1.66305E+18',
                    'confirmation': 10,
                    'status': 'SUCCESS',
                    'created_at': '2022-01-12 04:10:54',
                    'updated_at': '2022-01-12 04:10:54',
                    'token': {
                        'name': 'Singularity Ethereum',
                        'symbol': 'AGIX',
                        'allowed_decimal': 5,
                        'blockchain': {
                            'name': 'Ethereum',
                            'symbol': 'ETH',
                            'chain_id': 42}}},
                    {
                        'id': '1df60a2369f34247a5dc3ed29a8eef67',
                        'transaction_operation': 'TOKEN_RECEIVED',
                        'transaction_hash': '22477fd4ea994689a04646cbbaafd133',
                        'transaction_amount': '1.66305E+18',
                        'confirmation': 10,
                        'status': 'WAITING_FOR_CONFIRMATION',
                        'created_at': '2022-01-12 04:10:54',
                        'updated_at': '2022-01-12 04:10:54',
                        'token': {
                            'name': 'Singularity Cardano',
                            'symbol': 'AGIX',
                            'allowed_decimal': 10,
                            'blockchain': {
                                'name': 'Cardano',
                                'symbol': 'ADA',
                                'chain_id': 2}}}]}],
            'meta': {'total_records': 3, 'page_count': 1,
                     'page_number': 1, 'page_size': 15}},
                                         'error': {'code': None, 'message': None, 'details': None}}
        success_response_with_no_history = {'status': 'success', 'data': {'items': [],
                                                                          'meta': {'total_records': 0, 'page_count': 0,
                                                                                   'page_number': 1, 'page_size': 15}},
                                            'error': {'code': None, 'message': None, 'details': None}}

        # Bad Request
        event = dict()
        response = get_conversion_history(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        event = {"queryStringParameters": {"address": 4477, "page_number": "random number"}}
        response = get_conversion_history(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        event = {"queryStringParameters": {"address": ""}}
        response = get_conversion_history(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_property_value_empty)

        event = {"queryStringParameters": {"address": "random address"}}
        response = get_conversion_count_by_status(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_ethereum_address)

        event = {"queryStringParameters": {"address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1", "page_size": "100"}}
        response = get_conversion_history(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_page_size_exceeds_limit)

        # valid request
        event = {"queryStringParameters": {"address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1"}}
        response = get_conversion_history(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, success_response_with_history)

        event = {"queryStringParameters": {"address": "0x27082A5dD14c4a265eC96e106d4cE4918b8Dd830"}}
        response = get_conversion_history(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, success_response_with_no_history)

    @patch("common.utils.Utils.report_slack")
    def test_get_conversion(self, mock_report_slack):
        event = dict()

        bad_request_property_value_empty = {'status': 'failed', 'data': None,
                                            'error': {'code': 'E0005', 'message': 'BAD_REQUEST',
                                                      'details': 'Property value is empty'}}
        bad_request_invalid_conversion_id = {'status': 'failed', 'data': None,
                                             'error': {'code': 'E0008', 'message': 'BAD_REQUEST',
                                                       'details': 'Invalid conversion id provided'}}
        success_response = {'status': 'success', 'data': {
            'conversion': {'id': '51769f201e46446fb61a9c197cb0706b', 'deposit_amount': '1.66305E+18',
                           'claim_amount': '1.638104E+18', 'fee_amount': '2.4946E+16', 'status': 'PROCESSING',
                           'created_at': '2022-01-10 04:10:54', 'updated_at': '2022-01-12 04:10:54'},
            'wallet_pair': {'from_address': '0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1',
                            'to_address': 'addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8',
                            'deposit_address': None},
            'from_token': {'name': 'Singularity Ethereum', 'symbol': 'AGIX', 'allowed_decimal': 5,
                           'blockchain': {'name': 'Ethereum', 'symbol': 'ETH', 'chain_id': 42}},
            'to_token': {'name': 'Singularity Cardano', 'symbol': 'AGIX', 'allowed_decimal': 10,
                         'blockchain': {'name': 'Cardano', 'symbol': 'ADA', 'chain_id': 2}}, 'transactions': [
                {'id': '391be6385abf4b608bdd20a44acd6abc', 'transaction_operation': 'TOKEN_RECEIVED',
                 'transaction_hash': '22477fd4ea994689a04646cbbaafd133', 'transaction_amount': '1.66305E+18',
                 'confirmation': 10, 'status': 'SUCCESS', 'created_at': '2022-01-12 04:10:54',
                 'updated_at': '2022-01-12 04:10:54',
                 'token': {'name': 'Singularity Ethereum', 'symbol': 'AGIX', 'allowed_decimal': 5,
                           'blockchain': {'name': 'Ethereum', 'symbol': 'ETH', 'chain_id': 42}}},
                {'id': '1df60a2369f34247a5dc3ed29a8eef67', 'transaction_operation': 'TOKEN_RECEIVED',
                 'transaction_hash': '22477fd4ea994689a04646cbbaafd133', 'transaction_amount': '1.66305E+18',
                 'confirmation': 10, 'status': 'WAITING_FOR_CONFIRMATION', 'created_at': '2022-01-12 04:10:54',
                 'updated_at': '2022-01-12 04:10:54',
                 'token': {'name': 'Singularity Cardano', 'symbol': 'AGIX', 'allowed_decimal': 10,
                           'blockchain': {'name': 'Cardano', 'symbol': 'ADA', 'chain_id': 2}}}]},
                            'error': {'code': None, 'message': None, 'details': None}}

        response = get_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_property_value_empty)

        response = get_conversion({"pathParameters": {"conversion_id": ""}}, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_property_value_empty)

        response = get_conversion({"pathParameters": {"conversion_id": "random conversion id "}}, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_conversion_id)

        response = get_conversion({"pathParameters": {"conversion_id": "51769f201e46446fb61a9c197cb0706b"}}, {})
        body = json.loads(response["body"])
        self.assertEqual(body, success_response)

    @patch("utils.blockchain.get_event_logs")
    @patch("common.blockchain_util.BlockChainUtil.contract_instance")
    @patch("common.blockchain_util.BlockChainUtil.load_contract")
    @patch("utils.blockchain.get_token_contract_path")
    @patch("utils.blockchain.get_cardano_transaction_details")
    @patch("utils.blockchain.get_ethereum_transaction_details")
    @patch("common.utils.Utils.report_slack")
    def test_create_transaction_for_conversion(self, mock_report_slack, mock_get_ethereum_transaction_details,
                                               mock_get_cardano_transaction_details, mock_get_token_contract_path,
                                               mock_load_contract, mock_contract_instance, mock_get_event_logs):
        mock_get_token_contract_path.return_value = "token.json"
        mock_load_contract.return_value = {"file": "data"}
        mock_contract_instance.return_value = {""}
        mock_get_event_logs.return_value = []

        conversion_repo.session.query(TransactionDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(ConversionTransactionDBModel).delete()
        conversion_repo.session.commit()

        bad_request_body_missing = {'status': 'failed', 'data': None,
                                    'error': {'code': 'E0001', 'message': 'BAD_REQUEST', 'details': 'Missing body'}}

        bad_request_schema_not_matching = {'status': 'failed', 'data': None,
                                           'error': {'code': 'E0003', 'message': 'BAD_REQUEST',
                                                     'details': 'Schema is not matching with request'}}
        bad_request_property_value_empty = {'status': 'failed', 'data': None,
                                            'error': {'code': 'E0005', 'message': 'BAD_REQUEST',
                                                      'details': 'Property value is empty'}}
        bad_request_invalid_conversion_id = {'status': 'failed', 'data': None,
                                             'error': {'code': 'E0008', 'message': 'BAD_REQUEST',
                                                       'details': 'Invalid conversion id provided'}}
        bad_request_transaction_already_created = {'status': 'failed', 'data': None,
                                                   'error': {'code': 'E0014', 'message': 'BAD_REQUEST',
                                                             'details': 'Transaction has been created already'}}
        bad_request_transaction_format_incorrect = {'status': 'failed', 'data': None,
                                                    'error': {'code': 'E0013', 'message': 'BAD_REQUEST',
                                                              'details': 'Transaction hash should be hex string with proper format'}}

        bad_request_transaction_not_found = {'status': 'failed', 'data': None,
                                             'error': {'code': 'E0011', 'message': 'BAD_REQUEST',
                                                       'details': 'Transaction hash is not found on the blockchain'}}
        unexpected_error_ethereum_transaction_details = {'status': 'failed', 'data': None,
                                                         'error': {'code': 'E0018', 'message': 'INTERNAL_SERVER_ERROR',
                                                                   'details': 'Unexpected error occurred while getting ethereum transaction details'}}
        bad_request_no_events_on_hash = {'status': 'failed', 'data': None,
                                         'error': {'code': 'E0067', 'message': 'BAD_REQUEST',
                                                   'details': 'Unable to find any events for the given hash'}}

        # Bad Request
        event = dict()
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_body_missing)

        body_input = json.dumps({})
        event["body"] = body_input
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        body_input = json.dumps({"conversion_id": "", "transaction_hash": ""})
        event["body"] = body_input
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_property_value_empty)

        body_input = json.dumps({"conversion_id": "random conversion id",
                                 "transaction_hash": "0xe5bd9472b9d9931ca41bc3598f2ec15665b77ef32c088da5f2f8f3d2f72782a9"})
        event["body"] = body_input
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_conversion_id)

        mock_get_ethereum_transaction_details.side_effect = BadRequestException(
            error_code=ErrorCode.RANDOM_TRANSACTION_HASH.value,
            error_details=ErrorDetails[ErrorCode.RANDOM_TRANSACTION_HASH.value].value)
        body_input = json.dumps({"conversion_id": "7298bce110974411b260cac758b37ee0",
                                 "transaction_hash": "random hash"})
        event["body"] = body_input
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_transaction_format_incorrect)

        mock_get_ethereum_transaction_details.side_effect = BadRequestException(
            error_code=ErrorCode.TRANSACTION_HASH_NOT_FOUND.value,
            error_details=ErrorDetails[ErrorCode.TRANSACTION_HASH_NOT_FOUND.value].value)
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_transaction_not_found)

        mock_get_ethereum_transaction_details.side_effect = InternalServerErrorException(
            error_code=ErrorCode.UNEXPECTED_ERROR_ETHEREUM_TRANSACTION_DETAILS.value,
            error_details=ErrorDetails[
                ErrorCode.UNEXPECTED_ERROR_ETHEREUM_TRANSACTION_DETAILS.value].value)
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, unexpected_error_ethereum_transaction_details)

        mock_get_ethereum_transaction_details.side_effect = None
        mock_get_ethereum_transaction_details.return_value = {"from": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1"}
        body_input = json.dumps({"conversion_id": "7298bce110974411b260cac758b37ee0",
                                 "transaction_hash": "0xe5bd9472b9d9931ca41bc3598f2ec15665b77ef32c088da5f2f8f3d2f72782a9"})
        event["body"] = body_input
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_no_events_on_hash)

        mock_get_event_logs.return_value = [{"args": {
            "tokenHolder": '0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1',
            "amount": 133305000,
            "conversionId": b'7298bce110974411b260cac758b37ee0'
        }}]
        event["body"] = body_input
        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body["status"], LambdaResponseStatus.SUCCESS.value)
        self.assertIsNotNone(body["data"]["id"])

        response = create_transaction_for_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body["status"], LambdaResponseStatus.FAILED.value)
        self.assertEqual(body, bad_request_transaction_already_created)

    @patch("application.service.conversion_service.get_signature")
    @patch("common.utils.Utils.report_slack")
    def test_claim_conversion(self, mock_report_slack, mock_signature):
        mock_signature.return_value = "some signature"
        event = dict()

        bad_request_missing_body = {'status': 'failed', 'data': None,
                                    'error': {'code': 'E0001', 'message': 'BAD_REQUEST', 'details': 'Missing body'}}
        bad_request_schema_not_matching = {'status': 'failed', 'data': None,
                                           'error': {'code': 'E0003', 'message': 'BAD_REQUEST',
                                                     'details': 'Schema is not matching with request'}}
        bad_request_property_value_empty = {'status': 'failed', 'data': None,
                                            'error': {'code': 'E0005', 'message': 'BAD_REQUEST',
                                                      'details': 'Property value is empty'}}
        bad_request_invalid_conversion_id = {'status': 'failed', 'data': None,
                                             'error': {'code': 'E0008', 'message': 'BAD_REQUEST',
                                                       'details': 'Invalid conversion id provided'}}
        bad_request_conversion_not_ready_for_claim = {'status': 'failed', 'data': None,
                                                      'error': {'code': 'E0052', 'message': 'BAD_REQUEST',
                                                                'details': 'Conversion is not ready for claim'}}
        bad_request_invalid_claim_for_blockchain = {'status': 'failed', 'data': None,
                                                    'error': {'code': 'E0053', 'message': 'BAD_REQUEST',
                                                              'details': 'Invalid claim operation for the blockchain'}}
        bad_request_incorrect_signature_value_or_length = {'status': 'failed', 'data': None,
                                                           'error': {'code': 'E0055', 'message': 'BAD_REQUEST',
                                                                     'details': 'Incorrect signature value or length provided'}}
        bad_request_invalid_signature = {'status': 'failed', 'data': None,
                                         'error': {'code': 'E0006', 'message': 'BAD_REQUEST',
                                                   'details': 'Incorrect signature provided'}}
        success_response = {'status': 'success', 'data': {'claim_amount': '1E+3', 'signature': 'some signature',
                                                          'contract_address': '0xacontractaddress'},
                            'error': {'code': None, 'message': None, 'details': None}}

        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_missing_body)

        body = {}
        event = {"pathParameters": {"conversion_id": ""}, "body": json.dumps(body)}
        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        body = {"from_address": "",
                "to_address": "",
                "amount": "",
                "signature": ""}
        event = {"body": json.dumps(body)}
        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_property_value_empty)

        body = {"from_address": "test",
                "to_address": "test",
                "amount": "re",
                "signature": "ee"}
        event = {"pathParameters": {"conversion_id": "test"}, "body": json.dumps(body)}
        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_conversion_id)

        conversion_repo.update_conversion(conversion_id="51769f201e46446fb61a9c197cb0706b", claim_amount=Decimal(1000),
                                          deposit_amount=Decimal(1000), fee_amount=None, status="PROCESSING",
                                          claim_signature=None)

        body = {"from_address": "test",
                "to_address": "test",
                "amount": "re",
                "signature": "ee"}
        event = {"pathParameters": {"conversion_id": "51769f201e46446fb61a9c197cb0706b"}, "body": json.dumps(body)}
        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_claim_for_blockchain)

        conversion_repo.update_conversion(conversion_id="5086b5245cd046a68363d9ca8ed0027e", claim_amount=Decimal(1000),
                                          deposit_amount=Decimal(1000), fee_amount=None, status="PROCESSING",
                                          claim_signature=None)

        body = {"from_address": "test",
                "to_address": "test",
                "amount": "re",
                "signature": "ee"}
        event = {"pathParameters": {"conversion_id": "5086b5245cd046a68363d9ca8ed0027e"}, "body": json.dumps(body)}
        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_conversion_not_ready_for_claim)

        conversion_repo.update_conversion(conversion_id="5086b5245cd046a68363d9ca8ed0027e", claim_amount=Decimal(1000),
                                          deposit_amount=Decimal(1000), fee_amount=None,
                                          status=ConversionStatus.WAITING_FOR_CLAIM.value,
                                          claim_signature=None)
        body = {"from_address": "test",
                "to_address": "test",
                "amount": "re",
                "signature": "ee"}
        event = {"pathParameters": {"conversion_id": "5086b5245cd046a68363d9ca8ed0027e"}, "body": json.dumps(body)}
        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_incorrect_signature_value_or_length)

        body = {"from_address": "test",
                "to_address": "test",
                "amount": "re",
                "signature": "0xd4159d88ccc844ced5f0fa19b2975877813ab82f5c260d8cbacc1c11e9d61e8c776db78473a052ee02da961e98c7326f70c5e37e9caa2240dbb17baea2d4c69c1b"}
        event = {"pathParameters": {"conversion_id": "5086b5245cd046a68363d9ca8ed0027e"}, "body": json.dumps(body)}
        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_signature)

        body = {
            "from_address": "addr_test1qza8485avt2xn3vy63plawqt0gk3ykpf98wusc4qrml2avu0pkm5rp3pkz6q4n3kf8znlf3y749lll8lfmg5x86kgt8qju7vx8",
            "to_address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1",
            "amount": "1000",
            "signature": "0x3b8421d9795dc5a9fd3f46ca109b603367033d7bab882c67c09d60e6b3dd4eec6b3e7a19bd1ce92f9fcba23f33d263fff3e850ac5bbeb24b029fbca9ae6786731b"}
        event = {"pathParameters": {"conversion_id": "5086b5245cd046a68363d9ca8ed0027e"}, "body": json.dumps(body)}
        response = claim_conversion(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, success_response)

    @patch("common.utils.Utils.report_slack")
    def test_get_conversion_count_by_status(self, mock_report_slack):
        bad_request_schema_not_matching = {'status': 'failed', 'data': None,
                                           'error': {'code': 'E0003', 'message': 'BAD_REQUEST',
                                                     'details': 'Schema is not matching with request'}}
        bad_request_property_value_empty = {'status': 'failed', 'data': None,
                                            'error': {'code': 'E0005', 'message': 'BAD_REQUEST',
                                                      'details': 'Property value is empty'}}
        bad_request_invalid_ethereum_address = {'status': 'failed', 'data': None,
                                                'error': {'code': 'E0059', 'message': 'BAD_REQUEST',
                                                          'details': 'Invalid ethereum address provided'}}
        success_response = {'status': 'success',
                            'data': {'overall_count': 3, 'each': {'USER_INITIATED': 2, 'PROCESSING': 1}},
                            'error': {'code': None, 'message': None, 'details': None}}
        success_response_non_register_address = {'status': 'success', 'data': {'overall_count': 0, 'each': {}},
                                                 'error': {'code': None, 'message': None, 'details': None}}

        # Bad Request
        event = dict()
        response = get_conversion_count_by_status(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        event = {"queryStringParameters": {"address": 4477}}
        response = get_conversion_count_by_status(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        event = {"queryStringParameters": {"address": ""}}
        response = get_conversion_count_by_status(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_property_value_empty)

        event = {"queryStringParameters": {"address": "random address"}}
        response = get_conversion_count_by_status(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_ethereum_address)

        # valid request
        event = {"queryStringParameters": {"address": "0xa18b95A9371Ac18C233fB024cdAC5ef6300efDa1"}}
        response = get_conversion_count_by_status(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, success_response)

        event = {"queryStringParameters": {"address": "0xb3D785784136E96290E74F4E06e2d0695882B0C7"}}
        response = get_conversion_count_by_status(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, success_response_non_register_address)

    @patch("common.utils.Utils.report_slack")
    def test_expire_conversion(self, mock_report_slack):
        conversions = conversion_repo.session.query(ConversionDBModel).filter(
            ConversionDBModel.status == ConversionStatus.EXPIRED.value).all()
        self.assertEqual(len(conversions), 0)

        expire_conversion({}, {})

        conversions = conversion_repo.session.query(ConversionDBModel).filter(
            ConversionDBModel.status == ConversionStatus.EXPIRED.value).all()
        self.assertEqual(len(conversions), 2)

    @patch("common.utils.Utils.report_slack")
    def test_get_transaction_by_conversion_id(self, mock_report_slack):
        bad_request_schema_not_matching = {'status': 'failed', 'data': None,
                                           'error': {'code': 'E0003', 'message': 'BAD_REQUEST',
                                                     'details': 'Schema is not matching with request'}}
        bad_request_property_value_empty = {'status': 'failed', 'data': None,
                                            'error': {'code': 'E0005', 'message': 'BAD_REQUEST',
                                                      'details': 'Property value is empty'}}
        bad_request_invalid_conversion_id = {'status': 'failed', 'data': None,
                                             'error': {'code': 'E0008', 'message': 'BAD_REQUEST',
                                                       'details': 'Invalid conversion id provided'}}
        success_response_no_transactions = {'status': 'success', 'data': [],
                                            'error': {'code': None, 'message': None, 'details': None}}
        success_response_with_transactions = {'status': 'success', 'data': [
            {'id': '391be6385abf4b608bdd20a44acd6abc', 'transaction_operation': 'TOKEN_RECEIVED',
             'transaction_hash': '22477fd4ea994689a04646cbbaafd133', 'transaction_amount': '1.66305E+18',
             'confirmation': 10, 'status': 'SUCCESS', 'created_at': '2022-01-12 04:10:54',
             'updated_at': '2022-01-12 04:10:54',
             'token': {'name': 'Singularity Ethereum', 'symbol': 'AGIX', 'allowed_decimal': 5,
                       'blockchain': {'name': 'Ethereum', 'symbol': 'ETH', 'chain_id': 42}}},
            {'id': '1df60a2369f34247a5dc3ed29a8eef67', 'transaction_operation': 'TOKEN_RECEIVED',
             'transaction_hash': '22477fd4ea994689a04646cbbaafd133', 'transaction_amount': '1.66305E+18',
             'confirmation': 10, 'status': 'WAITING_FOR_CONFIRMATION', 'created_at': '2022-01-12 04:10:54',
             'updated_at': '2022-01-12 04:10:54',
             'token': {'name': 'Singularity Cardano', 'symbol': 'AGIX', 'allowed_decimal': 10,
                       'blockchain': {'name': 'Cardano', 'symbol': 'ADA', 'chain_id': 2}}}],
                                              'error': {'code': None, 'message': None, 'details': None}}

        event = dict()

        # bad requests
        response = get_transaction_by_conversion_id(event, None)
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        event["queryStringParameters"] = dict()
        response = get_transaction_by_conversion_id(event, None)
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_schema_not_matching)

        event["queryStringParameters"]["conversion_id"] = ""
        response = get_transaction_by_conversion_id(event, None)
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_property_value_empty)

        event["queryStringParameters"]["conversion_id"] = "random id"
        response = get_transaction_by_conversion_id(event, None)
        body = json.loads(response["body"])
        self.assertEqual(body, bad_request_invalid_conversion_id)

        # valid requests
        event["queryStringParameters"]["conversion_id"] = "7298bce110974411b260cac758b37ee0"
        response = get_transaction_by_conversion_id(event, None)
        body = json.loads(response["body"])
        self.assertEqual(body, success_response_no_transactions)

        event["queryStringParameters"]["conversion_id"] = "51769f201e46446fb61a9c197cb0706b"
        response = get_transaction_by_conversion_id(event, None)
        body = json.loads(response["body"])
        self.assertEqual(body, success_response_with_transactions)

    def tearDown(self):
        TestConversion.delete_all_tables()

    @staticmethod
    def delete_all_tables():
        conversion_repo.session.query(TransactionDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(ConversionTransactionDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(ConversionDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(WalletPairDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(TokenPairDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(ConversionFeeDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(TokenDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(BlockChainDBModel).delete()
        conversion_repo.session.commit()
        conversion_repo.session.query(MessageGroupPoolDBModel).delete()
        conversion_repo.session.commit()
