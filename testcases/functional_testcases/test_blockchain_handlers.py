import json
import unittest
from unittest.mock import patch

from application.handler.blockchain_handlers import get_all_blockchain
from infrastructure.models import BlockChainDBModel, TransactionDBModel, ConversionTransactionDBModel, \
    ConversionDBModel, WalletPairDBModel, TokenPairDBModel, ConversionFeeDBModel, TokenDBModel, MessageGroupPoolDBModel
from infrastructure.repositories.blockchain_repository import BlockchainRepository
from testcases.functional_testcases.test_variables import TestVariables

blockchain_repo = BlockchainRepository()


class TestBlockchain(unittest.TestCase):

    def setUp(self):
        self.tearDown()
        blockchain_repo.session.add_all(TestVariables().blockchain)
        blockchain_repo.session.commit()

    @patch("common.utils.Utils.report_slack")
    def test_get_all_blockchain(self, mock_report_slack):
        success_response_1 = {'status': 'success', 'data': [
            {'id': 'a38b4038c3a04810805fb26056dfabdd', 'name': 'Ethereum', 'description': 'Connect with your wallet',
             'symbol': 'ETH', 'logo': 'www.ethereum.com/image.png', 'is_extension_available': True, 'chain_id': 42,
             'block_confirmation': 25, 'updated_at': '2022-01-12 04:10:54'},
            {'id': '5b21294fe71a4145a40f6ab918a50f96', 'name': 'Cardano', 'description': 'Add your wallet address',
             'symbol': 'ADA', 'logo': 'www.cardano.com/image.png', 'is_extension_available': False, 'chain_id': 2,
             'block_confirmation': 23, 'updated_at': '2022-01-12 04:10:54'}],
                              'error': {'code': None, 'message': None, 'details': None}}
        success_response_2 = {'status': 'success', 'data': [],
                              'error': {'code': None, 'message': None, 'details': None}}

        event = dict()
        # when data is seeded
        response = get_all_blockchain(event, {})
        print(response["body"])
        body = json.loads(response["body"])
        self.assertEqual(body, success_response_1)

        self.tearDown()

        # when data is not seeded
        response = get_all_blockchain(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body, success_response_2)

    def tearDown(self):
        blockchain_repo.session.query(TransactionDBModel).delete()
        blockchain_repo.session.commit()
        blockchain_repo.session.query(ConversionTransactionDBModel).delete()
        blockchain_repo.session.commit()
        blockchain_repo.session.query(ConversionDBModel).delete()
        blockchain_repo.session.commit()
        blockchain_repo.session.query(WalletPairDBModel).delete()
        blockchain_repo.session.commit()
        blockchain_repo.session.query(TokenPairDBModel).delete()
        blockchain_repo.session.commit()
        blockchain_repo.session.query(ConversionFeeDBModel).delete()
        blockchain_repo.session.commit()
        blockchain_repo.session.query(TokenDBModel).delete()
        blockchain_repo.session.commit()
        blockchain_repo.session.query(BlockChainDBModel).delete()
        blockchain_repo.session.commit()
        blockchain_repo.session.query(MessageGroupPoolDBModel).delete()
        blockchain_repo.session.commit()
