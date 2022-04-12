import json
from decimal import Decimal

from application.service.conversion_reponse import get_latest_user_pending_conversion_request_response, \
    create_conversion_response, create_conversion_request_response, \
    get_conversion_detail_response, get_conversion_history_response, create_conversion_transaction_response, \
    create_transaction_response, create_transaction_for_conversion_response, get_transaction_by_hash_response, \
    claim_conversion_response, \
    get_conversion_response, update_conversion_response, get_expiring_conversion_response, get_transaction_response
from application.service.token_service import TokenService
from application.service.wallet_pair_service import WalletPairService
from common.blockchain_util import BlockChainUtil
from common.logger import get_logger
from common.utils import Utils
from config import SIGNATURE_EXPIRY_BLOCK_NUMBER, EXPIRE_CONVERSION, CONVERTER_REPORTING_SLACK_HOOK
from constants.entity import TokenPairEntities, WalletPairEntities, \
    ConversionEntities, TokenEntities, BlockchainEntities, ConversionDetailEntities, TransactionConversionEntities, \
    TransactionEntities, ConversionFeeEntities, ConverterBridgeEntities, EventConsumerEntity
from constants.error_details import ErrorCode, ErrorDetails
from constants.general import BlockchainName, CreatedBy, SignatureTypeEntities, ConversionOn
from constants.status import ConversionStatus, TransactionVisibility, TransactionStatus
from infrastructure.repositories.conversion_repository import ConversionRepository
from utils.blockchain import validate_address, validate_conversion_claim_request_signature, \
    calculate_fee_amount, \
    validate_conversion_request_amount, convert_str_to_decimal, get_next_activity_event_on_conversion, \
    check_existing_transaction_state, validate_ethereum_transaction_details_against_conversion, \
    validate_cardano_transaction_details_against_conversion
from utils.exceptions import BadRequestException, InternalServerErrorException
from utils.general import get_blockchain_from_token_pair_details, get_response_from_entities, \
    is_supported_network_conversion, get_ethereum_network_url, get_offset, paginate_items_response_format, \
    datetime_in_utcnow, relative_date, datetime_to_str, get_formatted_conversion_status_report
from utils.signature import validate_conversion_signature, get_signature

logger = get_logger(__name__)


class ConversionService:

    def __init__(self):
        self.conversion_repo = ConversionRepository()
        self.token_service = TokenService()
        self.wallet_pair_service = WalletPairService()

    def create_conversion(self, wallet_pair_id, deposit_amount, fee_amount, claim_amount,
                          created_by=CreatedBy.DAPP.value):
        logger.info(f"Creating the conversion with wallet_pair_id={wallet_pair_id}, deposit_amount={deposit_amount}, "
                    f" fee_amount={fee_amount} claim_amount={claim_amount} created_by={created_by}")
        conversion = self.conversion_repo.create_conversion(wallet_pair_id=wallet_pair_id,
                                                            deposit_amount=deposit_amount, fee_amount=fee_amount,
                                                            claim_amount=claim_amount, created_by=created_by)
        return create_conversion_response(conversion.to_dict())

    def create_conversion_transaction(self, conversion_id, created_by):
        logger.info(f"Creating the conversion transaction = {conversion_id}, created_by={created_by}")
        conversion_transaction = self.conversion_repo.create_conversion_transaction(conversion_id=conversion_id,
                                                                                    created_by=created_by)
        return create_conversion_transaction_response(conversion_transaction.to_dict())

    def create_transaction(self, conversion_transaction_id, token_id, transaction_visibility,
                           transaction_operation, transaction_hash, transaction_amount, confirmation, status,
                           created_by):
        logger.info(f"Creating the transaction with the details conversion_transaction_id={conversion_transaction_id},"
                    f" token_id={token_id}, transaction_visibility="
                    f"{transaction_visibility}, transaction_operation={transaction_operation}, "
                    f"transaction_hash={transaction_hash}, transaction_amount={transaction_amount}, "
                    f" confirmation={confirmation}, status={status}, created_by={created_by}")
        transaction = self.conversion_repo.create_transaction(conversion_transaction_id=conversion_transaction_id,
                                                              token_id=token_id,
                                                              transaction_visibility=transaction_visibility,
                                                              transaction_operation=transaction_operation,
                                                              transaction_hash=transaction_hash,
                                                              transaction_amount=transaction_amount,
                                                              confirmation=confirmation, status=status,
                                                              created_by=created_by)
        return create_transaction_response(transaction.to_dict())

    def __get_conversion_only(self, conversion_id):
        logger.info(f"Getting only the conversion for the given conversion_id={conversion_id}")
        conversion = self.conversion_repo.get_conversion_only(conversion_id)

        if conversion is None:
            raise BadRequestException(error_code=ErrorCode.INVALID_CONVERSION_ID.value,
                                      error_details=ErrorDetails[ErrorCode.INVALID_CONVERSION_ID.value].value)

        return conversion.to_dict()

    def get_conversion(self, conversion_id):
        logger.info(f"Getting the conversion for the conversion_id={conversion_id} ")
        conversion = self.get_conversion_complete_detail(conversion_id=conversion_id)

        if conversion is None:
            raise BadRequestException(error_code=ErrorCode.INVALID_CONVERSION_ID.value,
                                      error_details=ErrorDetails[ErrorCode.INVALID_CONVERSION_ID.value].value)

        return get_conversion_response(conversion)

    def get_conversion_detail_by_tx_id(self, tx_id):
        logger.info(f"Get the conversion detail by tx_id={tx_id}")
        conversion = self.conversion_repo.get_conversion_detail_by_tx_id(tx_id)
        return conversion.to_dict()

    def __get_conversion_detail(self, conversion_id):
        logger.info(f"Get the conversion detail for the conversion_id={conversion_id}")
        conversion_detail = self.conversion_repo.get_conversion_detail(conversion_id=conversion_id)
        if conversion_detail:
            conversion_detail = conversion_detail.to_dict()
            conversion_row_ids = ConversionService.get_conversion_row_ids(conversion_details=[conversion_detail])
            transaction_details = dict()
            if conversion_row_ids:
                transaction_details = self.get_transactions_for_conversion_row_ids(
                    conversion_row_ids=conversion_row_ids)
            transaction_details = self.format_transactions_with_conversion(transaction_details=transaction_details)
            conversion_details = self.add_transaction_detail_to_conversion_detail(
                conversion_details=[conversion_detail],
                transaction_details=transaction_details)
            conversion_detail = conversion_details[0]
        return conversion_detail

    def get_conversion_detail(self, conversion_id):
        logger.info(f"Get the conversion for the ID={conversion_id}")
        conversion_detail = self.__get_conversion_detail(conversion_id=conversion_id)

        if conversion_detail is None:
            raise BadRequestException(error_code=ErrorCode.INVALID_CONVERSION_ID.value,
                                      error_details=ErrorDetails[ErrorCode.INVALID_CONVERSION_ID.value].value)

        return get_conversion_detail_response(conversion_detail)

    def get_latest_user_pending_conversion_request(self, wallet_pair_id):
        conversion = self.conversion_repo.get_latest_user_pending_conversion_request(wallet_pair_id=wallet_pair_id,
                                                                                     status=ConversionStatus.USER_INITIATED.value)
        return get_latest_user_pending_conversion_request_response(conversion.to_dict()) if conversion else None

    def update_conversion_status(self, conversion_id, status):
        logger.info(f"Updating the conversion status for the conversion_id={conversion_id}, "
                    f"status={status}")
        self.conversion_repo.update_conversion_status(conversion_id=conversion_id, status=status)

    def update_conversion(self, conversion_id, deposit_amount=None, claim_amount=None, fee_amount=None, status=None,
                          claim_signature=None):
        logger.info(f"Updating the conversion  for the conversion_id={conversion_id}, "
                    f"deposit_amount={deposit_amount}, claim_amount={claim_amount}, fee_amount={fee_amount}, "
                    f"status={status}, claim_signature={claim_signature}")
        conversion = self.conversion_repo.update_conversion(conversion_id=conversion_id, deposit_amount=deposit_amount,
                                                            claim_amount=claim_amount, fee_amount=fee_amount,
                                                            status=status, claim_signature=claim_signature)
        return update_conversion_response(conversion.to_dict())

    def update_conversion_transaction(self, conversion_transaction_id, status):
        logger.info(
            f"Updating the conversion transaction for the conversion_transaction_id={conversion_transaction_id}, "
            f"status={status}")
        self.conversion_repo.update_conversion_transaction(conversion_transaction_id=conversion_transaction_id,
                                                           status=status)

    @staticmethod
    def create_conversion_request_validation(token_pair_id, amount, from_address, to_address, block_number,
                                             signature, token_pair):
        logger.info("Validating  the conversion request")
        is_signer_as_from_address = False
        from_blockchain = get_blockchain_from_token_pair_details(token_pair=token_pair,
                                                                 blockchain_conversion_type=TokenPairEntities.FROM_TOKEN.value)
        to_blockchain = get_blockchain_from_token_pair_details(token_pair=token_pair,
                                                               blockchain_conversion_type=TokenPairEntities.TO_TOKEN.value)

        if not is_supported_network_conversion(from_blockchain=from_blockchain, to_blockchain=to_blockchain):
            logger.exception(
                f"Unsupported network conversion detected from_blockchain={from_blockchain}, to_blockchain={to_blockchain}")
            raise InternalServerErrorException(error_code=ErrorCode.UNSUPPORTED_CHAIN_ID.value,
                                               error_details=ErrorDetails[
                                                   ErrorCode.UNSUPPORTED_CHAIN_ID.value].value)

        from_blockchain_name = from_blockchain.get(BlockchainEntities.NAME.value)

        if from_blockchain_name.lower() == BlockchainName.ETHEREUM.value.lower():
            is_signer_as_from_address = True
            chain_id = from_blockchain.get(BlockchainEntities.CHAIN_ID.value)
        else:
            chain_id = to_blockchain.get(BlockchainEntities.CHAIN_ID.value)

        network_url = get_ethereum_network_url(chain_id=chain_id)
        ethereum_web3_object = BlockChainUtil(provider_type="HTTP_PROVIDER", provider=network_url)
        current_block_no = ethereum_web3_object.get_current_block_no()
        if not block_number <= current_block_no or block_number < (current_block_no - SIGNATURE_EXPIRY_BLOCK_NUMBER):
            raise BadRequestException(error_code=ErrorCode.SIGNATURE_EXPIRED.value,
                                      error_details=ErrorDetails[ErrorCode.SIGNATURE_EXPIRED.value].value)

        result = validate_conversion_signature(token_pair_id=token_pair_id, amount=amount, from_address=from_address,
                                               to_address=to_address, block_number=block_number, signature=signature,
                                               is_signer_as_from_address=is_signer_as_from_address, chain_id=chain_id)
        if result is False:
            raise BadRequestException(error_code=ErrorCode.INCORRECT_SIGNATURE.value,
                                      error_details=ErrorDetails[ErrorCode.INCORRECT_SIGNATURE.value].value)

        validate_address(from_address=from_address, to_address=to_address, from_blockchain=from_blockchain,
                         to_blockchain=to_blockchain)

    def create_conversion_request(self, token_pair_id, amount, from_address, to_address, block_number, signature):
        logger.info(f"Creating the conversion request for token_pair_id={token_pair_id}, amount={amount}, "
                    f"from_address={from_address}, to_address={to_address}, block_number={block_number}, "
                    f"signature={signature}")
        contract_signature = None
        fee_amount = Decimal(0)
        contract_address = None

        token_pair = self.token_service.get_token_pair_internal(token_pair_id=token_pair_id)

        validate_conversion_request_amount(amount=amount,
                                           min_value=token_pair.get(TokenPairEntities.MIN_VALUE.value),
                                           max_value=token_pair.get(TokenPairEntities.MAX_VALUE.value))

        ConversionService.create_conversion_request_validation(token_pair_id=token_pair_id, amount=amount,
                                                               from_address=from_address, to_address=to_address,
                                                               block_number=block_number, signature=signature,
                                                               token_pair=token_pair)
        wallet_pair = self.wallet_pair_service.persist_wallet_pair_details(from_address=from_address,
                                                                           to_address=to_address, amount=amount,
                                                                           signature=signature,
                                                                           block_number=block_number,
                                                                           token_pair=token_pair)
        amount = convert_str_to_decimal(value=amount)

        if token_pair.get(TokenPairEntities.CONVERSION_FEE.value):
            fee_amount = calculate_fee_amount(amount=amount, percentage=token_pair.get(
                TokenPairEntities.CONVERSION_FEE.value).get(ConversionFeeEntities.PERCENTAGE_FROM_SOURCE.value))

        from_blockchain_name = token_pair.get(TokenPairEntities.FROM_TOKEN.value).get(
            TokenEntities.BLOCKCHAIN.value).get(BlockchainEntities.NAME.value)
        conversion = self.process_conversion_request(wallet_pair_id=wallet_pair.get(WalletPairEntities.ROW_ID.value),
                                                     deposit_amount=amount, fee_amount=fee_amount,
                                                     from_blockchain_name=from_blockchain_name)

        conversion_id = conversion[ConversionEntities.ID.value]
        deposit_address = wallet_pair[WalletPairEntities.DEPOSIT_ADDRESS.value]
        deposit_amount = conversion.get(ConversionEntities.DEPOSIT_AMOUNT.value)

        if not deposit_address:
            user_address = wallet_pair.get(WalletPairEntities.FROM_ADDRESS.value)
            contract_address = self.get_token_contract_address_for_conversion_id(conversion_id=conversion_id)
            contract_signature = get_signature(signature_type=SignatureTypeEntities.CONVERSION_OUT.value,
                                               user_address=user_address, conversion_id=conversion_id,
                                               amount=convert_str_to_decimal(deposit_amount),
                                               contract_address=contract_address,
                                               chain_id=token_pair.get(
                                                   TokenPairEntities.FROM_TOKEN.value).get(
                                                   TokenEntities.BLOCKCHAIN.value).get(
                                                   BlockchainEntities.CHAIN_ID.value))
        return create_conversion_request_response(conversion_id=conversion_id, deposit_address=deposit_address,
                                                  signature=contract_signature, deposit_amount=deposit_amount,
                                                  contract_address=contract_address)

    def validate_transaction_hash(self, conversion_detail, transaction_hash, created_by):
        transaction = self.get_transaction_by_hash(tx_hash=transaction_hash)

        if transaction:
            raise BadRequestException(error_code=ErrorCode.TRANSACTION_ALREADY_CREATED.value,
                                      error_details=ErrorDetails[ErrorCode.TRANSACTION_ALREADY_CREATED.value].value)

        transactions = conversion_detail.get(ConversionDetailEntities.TRANSACTIONS.value)
        conversion = conversion_detail.get(ConversionDetailEntities.CONVERSION.value)

        from_blockchain = conversion_detail.get(ConversionDetailEntities.FROM_TOKEN.value, {}).get(
            TokenEntities.BLOCKCHAIN.value, {})
        to_blockchain = conversion_detail.get(ConversionDetailEntities.TO_TOKEN.value, {}).get(
            TokenEntities.BLOCKCHAIN.value, {})

        if not is_supported_network_conversion(from_blockchain=from_blockchain, to_blockchain=to_blockchain):
            logger.exception(
                f"Unsupported network conversion detected from_blockchain={from_blockchain}, to_blockchain={to_blockchain}")
            raise InternalServerErrorException(error_code=ErrorCode.UNSUPPORTED_CHAIN_ID.value,
                                               error_details=ErrorDetails[ErrorCode.UNSUPPORTED_CHAIN_ID.value].value)

        next_activity = get_next_activity_event_on_conversion(conversion_complete_detail=conversion_detail)
        if next_activity is None:
            raise BadRequestException(error_code=ErrorCode.CONVERSION_ALREADY_DONE.value,
                                      error_details=ErrorDetails[ErrorCode.CONVERSION_ALREADY_DONE.value].value)

        if next_activity.get(ConverterBridgeEntities.BLOCKCHAIN_NAME.value).lower() == from_blockchain.get(
                BlockchainEntities.NAME.value).lower():
            conversion_on = ConversionOn.FROM.value
            blockchain = from_blockchain
        else:
            conversion_on = ConversionOn.TO.value
            blockchain = to_blockchain

        blockchain_name = blockchain.get(BlockchainEntities.NAME.value).lower()
        chain_id = blockchain.get(BlockchainEntities.CHAIN_ID.value)

        if created_by == CreatedBy.DAPP.value and blockchain_name.lower() == BlockchainName.CARDANO.value.lower():
            raise BadRequestException(error_code=ErrorCode.DAPP_AUTHORIZED_FOR_CARDANO_TX_UPDATE.value,
                                      error_details=ErrorDetails[
                                          ErrorCode.DAPP_AUTHORIZED_FOR_CARDANO_TX_UPDATE.value].value)

        check_existing_transaction_state(transactions=transactions, conversion_on=conversion_on)

        if blockchain_name == BlockchainName.ETHEREUM.value.lower():
            contract_address = self.get_token_contract_address_for_conversion_id(
                conversion_id=conversion.get(ConversionEntities.ID.value))
            validate_ethereum_transaction_details_against_conversion(chain_id=chain_id,
                                                                     transaction_hash=transaction_hash,
                                                                     conversion_on=conversion_on,
                                                                     contract_address=contract_address,
                                                                     conversion_detail=conversion_detail)
        elif blockchain_name == BlockchainName.CARDANO.value.lower():
            validate_cardano_transaction_details_against_conversion(chain_id=chain_id,
                                                                    transaction_hash=transaction_hash,
                                                                    conversion_on=conversion_on,
                                                                    conversion_detail=conversion_detail)
        return next_activity

    def process_conversion_request(self, wallet_pair_id: str, deposit_amount: Decimal, fee_amount: Decimal,
                                   from_blockchain_name, created_by: str = CreatedBy.DAPP.value):
        logger.info(f"Processing the conversion request with wallet_pair_id={wallet_pair_id},"
                    f" deposit_amount={deposit_amount}, fee_amount={fee_amount}, "
                    f"from_blockchain_name={from_blockchain_name}")
        conversion = None
        if from_blockchain_name != BlockchainName.ETHEREUM.value:
            conversion = self.get_latest_user_pending_conversion_request(wallet_pair_id=wallet_pair_id)

        if conversion and (created_by == CreatedBy.DAPP.value or
                           Decimal(float(conversion.get(ConversionEntities.DEPOSIT_AMOUNT.value))) != deposit_amount
                           or Decimal(float(conversion.get(ConversionEntities.FEE_AMOUNT.value))) != fee_amount):
            self.update_conversion(conversion_id=conversion[ConversionEntities.ID.value],
                                   status=ConversionStatus.EXPIRED.value)
            conversion = None

        if not conversion:
            conversion = self.create_conversion(wallet_pair_id=wallet_pair_id, deposit_amount=deposit_amount,
                                                fee_amount=fee_amount, claim_amount=deposit_amount - fee_amount,
                                                created_by=created_by)
        return conversion

    def get_token_contract_address_for_conversion_id(self, conversion_id):
        logger.info(f"Getting the token contract address for conversion_id={conversion_id}")
        return self.conversion_repo.get_token_contract_address_for_conversion_id(conversion_id)

    def get_conversion_history(self, address, page_size, page_number):
        logger.info(f"Getting the conversion history for the given address={address}, page_size={page_size}, "
                    f"page_number={page_number}")
        total_conversion_history = self.conversion_repo.get_conversion_history_count(address=address)
        offset = get_offset(page_number=page_number, page_size=page_size)

        if total_conversion_history and total_conversion_history > offset:
            conversion_history_obj = self.conversion_repo.get_conversion_history(address=address, conversion_id=None,
                                                                                 offset=offset, limit=page_size)
            conversion_history = get_response_from_entities(conversion_history_obj)

            conversion_row_ids = ConversionService.get_conversion_row_ids(conversion_details=conversion_history)
            transaction_details = dict()
            if conversion_row_ids:
                transaction_details = self.get_transactions_for_conversion_row_ids(
                    conversion_row_ids=conversion_row_ids)
            transaction_details = self.format_transactions_with_conversion(transaction_details=transaction_details)
            conversion_history = self.add_transaction_detail_to_conversion_detail(conversion_details=conversion_history,
                                                                                  transaction_details=transaction_details)
            conversion_detail_history_response = get_conversion_history_response(conversion_history)

        else:
            conversion_detail_history_response = []

        return paginate_items_response_format(items=conversion_detail_history_response,
                                              total_records=total_conversion_history,
                                              page_number=page_number, page_size=page_size)

    @staticmethod
    def get_conversion_row_ids(conversion_details):
        return [conversion_detail.get(ConversionDetailEntities.CONVERSION.value).get(ConversionEntities.ROW_ID.value)
                for conversion_detail in conversion_details]

    @staticmethod
    def format_transactions_with_conversion(transaction_details):
        formatted_transaction_details = {}
        for transaction_detail in transaction_details:
            conversion_row_id = transaction_detail.get(TransactionEntities.CONVERSION_TRANSACTION.value, {}).get(
                TransactionConversionEntities.CONVERSION_ID.value)
            formatted_transaction_details[conversion_row_id] = formatted_transaction_details.get(conversion_row_id, {})
            formatted_transaction_details[conversion_row_id][ConversionDetailEntities.TRANSACTIONS.value] = \
                formatted_transaction_details[
                    conversion_row_id].get(ConversionDetailEntities.TRANSACTIONS.value, [])
            formatted_transaction_details[conversion_row_id][ConversionDetailEntities.TRANSACTIONS.value].append(
                transaction_detail)
        return formatted_transaction_details

    @staticmethod
    def add_transaction_detail_to_conversion_detail(conversion_details, transaction_details):
        for conversion_detail in conversion_details:
            conversion_row_id = conversion_detail.get(ConversionDetailEntities.CONVERSION.value).get(
                ConversionEntities.ROW_ID.value)
            transaction_detail = transaction_details.get(conversion_row_id, {}).get("transactions", [])
            conversion_detail[ConversionDetailEntities.TRANSACTIONS.value] = transaction_detail
        return conversion_details

    def get_transaction_by_conversion_id(self, conversion_id):
        logger.info(f"Getting the transactions for the given conversion_id={conversion_id}")
        conversion = self.__get_conversion_only(conversion_id=conversion_id)
        transactions = self.get_transactions_for_conversion_row_ids(
            conversion_row_ids=[conversion.get(ConversionEntities.ROW_ID.value)])
        return get_transaction_response(transactions)

    def get_transactions_for_conversion_row_ids(self, conversion_row_ids):
        logger.info(f"Getting the transactions for the given conversion_row_ids={conversion_row_ids}")
        transaction_objs = self.conversion_repo.get_transactions_for_conversion_row_ids(
            conversion_row_ids=conversion_row_ids)
        return get_response_from_entities(transaction_objs)

    def get_conversion_complete_detail(self, conversion_id):
        logger.info(f"Getting the conversion complete detail")
        return self.__get_conversion_detail(conversion_id=conversion_id)

    @staticmethod
    def get_conversion_ids_from_conversion_detail(conversion_detail):
        conversion_ids = []
        for conversion in conversion_detail:
            conversion_ids.append(conversion["conversion"]["id"])
        return set(conversion_ids)

    def create_transaction_for_conversion(self, conversion_id, transaction_hash, created_by=CreatedBy.DAPP.value):
        logger.info(f"Creating the new transaction for the conversion_id={conversion_id} with "
                    f"transaction_hash={transaction_hash}, created_by={created_by}")
        conversion_detail = self.get_conversion_detail(conversion_id=conversion_id)
        next_activity = self.validate_transaction_hash(conversion_detail=conversion_detail,
                                                       transaction_hash=transaction_hash, created_by=created_by)
        transaction = self.process_transaction_creation(conversion_detail=conversion_detail,
                                                        transaction_hash=transaction_hash, next_activity=next_activity,
                                                        created_by=created_by)
        return create_transaction_for_conversion_response(transaction)

    def process_transaction_creation(self, conversion_detail, transaction_hash, next_activity, created_by):
        transaction = conversion_detail.get(ConversionDetailEntities.TRANSACTIONS.value)
        conversion_row_id = conversion_detail.get(ConversionDetailEntities.CONVERSION.value, {}).get(
            ConversionEntities.ROW_ID.value)
        conversion_id = conversion_detail.get(ConversionDetailEntities.CONVERSION.value, {}).get(
            ConversionEntities.ID.value)

        transaction_operation = next_activity.get(EventConsumerEntity.BLOCKCHAIN_EVENT.value).get(
            ConverterBridgeEntities.TX_OPERATION.value)

        if not len(transaction):
            token_id = conversion_detail.get(ConversionDetailEntities.FROM_TOKEN.value).get(
                TokenEntities.ROW_ID.value)
            conversion_transaction = self.create_conversion_transaction(conversion_id=conversion_row_id,
                                                                        created_by=created_by)
            conversion_transaction_row_id = conversion_transaction.get(TransactionConversionEntities.ROW_ID.value)
            transaction_amount = conversion_detail.get(ConversionDetailEntities.CONVERSION.value, {}).get(
                ConversionEntities.DEPOSIT_AMOUNT.value)
        else:
            token_id = conversion_detail.get(ConversionDetailEntities.TO_TOKEN.value).get(
                TokenEntities.ROW_ID.value)
            conversion_transaction_row_id = transaction[0].get(TransactionEntities.CONVERSION_TRANSACTION_ID.value)
            transaction_amount = conversion_detail.get(ConversionDetailEntities.CONVERSION.value, {}).get(
                ConversionEntities.CLAIM_AMOUNT.value)

        if transaction_amount is None:
            raise BadRequestException(error_code=ErrorCode.UNSUPPORTED_CHAIN_ID.value,
                                      error_details=ErrorDetails[ErrorCode.UNSUPPORTED_CHAIN_ID.value].value)

        transaction = self.create_transaction(conversion_transaction_id=conversion_transaction_row_id,
                                              token_id=token_id,
                                              transaction_visibility=TransactionVisibility.EXTERNAL.value,
                                              transaction_operation=transaction_operation,
                                              transaction_hash=transaction_hash, transaction_amount=transaction_amount,
                                              confirmation=0, status=TransactionStatus.WAITING_FOR_CONFIRMATION.value,
                                              created_by=created_by)
        self.update_conversion_status(conversion_id=conversion_id, status=ConversionStatus.PROCESSING.value)

        return transaction

    def update_transaction_by_id(self, tx_id, tx_operation=None, tx_visibility=None, tx_amount=None, confirmation=None,
                                 tx_status=None, created_by=None):
        logger.info(
            f"Updating the transaction of tx_id={tx_id}, tx_operation={tx_operation}, tx_visibility={tx_visibility}, "
            f"tx_amount={tx_amount}, confirmation={confirmation}, tx_status={tx_status}, created_by={created_by}")
        self.conversion_repo.update_transaction_by_id(tx_id=tx_id, tx_operation=tx_operation,
                                                      tx_visibility=tx_visibility, tx_amount=tx_amount,
                                                      confirmation=confirmation, tx_status=tx_status,
                                                      created_by=created_by)

    def get_transaction_by_hash(self, tx_hash):
        logger.info(f"Getting the transaction by tx_hash={tx_hash}")
        transaction = self.conversion_repo.get_transaction_by_hash(tx_hash)
        return get_transaction_by_hash_response(transaction.to_dict()) if transaction else None

    def claim_conversion(self, conversion_id, amount, from_address, to_address, signature):
        logger.info(
            f"Claim the conversion for the conversion_id={conversion_id}, amount={amount}, from_address={from_address},"
            f"to_address={to_address}, signature={signature}")
        conversion_detail = self.get_conversion_detail(conversion_id=conversion_id)
        chain_id = conversion_detail.get(ConversionDetailEntities.TO_TOKEN.value).get(
            TokenEntities.BLOCKCHAIN.value).get(BlockchainEntities.CHAIN_ID.value)

        # validate the request signature
        validate_conversion_claim_request_signature(conversion_detail=conversion_detail, amount=amount,
                                                    from_address=from_address, to_address=to_address,
                                                    signature=signature, chain_id=chain_id)

        conversion = conversion_detail.get(ConversionDetailEntities.CONVERSION.value)
        claim_amount = conversion.get(ConversionEntities.CLAIM_AMOUNT.value)
        user_address = conversion_detail.get(ConversionDetailEntities.WALLET_PAIR.value).get(
            WalletPairEntities.TO_ADDRESS.value)
        contract_address = self.get_token_contract_address_for_conversion_id(conversion_id=conversion_id)

        # Generate claim signature
        claim_signature = get_signature(signature_type=SignatureTypeEntities.CONVERSION_IN.value,
                                        user_address=user_address, conversion_id=conversion_id,
                                        amount=Decimal(float(claim_amount)),
                                        contract_address=contract_address, chain_id=chain_id)
        # Update the signature and status
        self.update_conversion(conversion_id=conversion_id, claim_signature=claim_signature)

        return claim_conversion_response(signature=claim_signature, claim_amount=claim_amount,
                                         contract_address=contract_address)

    def get_conversion_count_by_status(self, address):
        logger.info(f"Getting the conversion count by status for the address={address}")
        return self.conversion_repo.get_conversion_count_by_status(address=address)

    def expire_conversion(self):
        current_datetime = datetime_in_utcnow()
        cardano_expire_datetime = relative_date(date_time=current_datetime, hours=EXPIRE_CONVERSION.get("CARDANO", 0))
        ethereum_expire_datetime = relative_date(date_time=current_datetime, hours=EXPIRE_CONVERSION.get("ETHEREUM", 0))
        print(f"Expiring the conversion of ethereum and cardano  which is less than or  equal to "
              f"{ethereum_expire_datetime} and {cardano_expire_datetime} respectively ")
        conversions = self.conversion_repo.get_expiring_conversion(
            ethereum_expire_datetime=ethereum_expire_datetime,
            cardano_expire_datetime=cardano_expire_datetime)
        conversion_ids = get_expiring_conversion_response(get_response_from_entities(conversions))
        print(f"Expiring conversions total={len(conversion_ids)} conversion_ids={conversion_ids}")
        self.conversion_repo.set_conversions_to_expire(conversion_ids=conversion_ids)

    def generate_conversion_report(self):
        current_date = datetime_in_utcnow().date()
        previous_date_str = datetime_to_str(relative_date(current_date, days=1))

        # Generate report only for previous date
        self.__generate_conversion_report(start_date=previous_date_str, end_date=previous_date_str)

        # Generate report till previous date
        self.__generate_conversion_report(start_date=None, end_date=previous_date_str)

    def __generate_conversion_report(self, start_date, end_date):
        logger.info(f"Getting the conversion report from start_date={start_date} and end_date={end_date}")
        report = self.conversion_repo.generate_conversion_report(start_date=start_date, end_date=end_date)
        logger.info(json.dumps(report))
        formatted_content = get_formatted_conversion_status_report(start_date=start_date, end_date=end_date,
                                                                   report=report)
        Utils().report_slack(slack_msg=formatted_content, SLACK_HOOK=CONVERTER_REPORTING_SLACK_HOOK)
