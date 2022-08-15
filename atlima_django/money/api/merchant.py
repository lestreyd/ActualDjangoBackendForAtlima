from hashlib import sha256
import requests
import json

# АКТУАЛЬНАЯ СИСТЕМА ПЛАТЕЖЕЙ 
class TinkoffMerchantAPI:

    def init(self, *args, **kwargs):
        return self.buildQuery('Init', *args, **kwargs)

    def get_state(self, *args, **kwargs):
        return self.buildQuery('GetState', *args, **kwargs)

    def confirm(self, *args, **kwargs):
        return self.buildQuery('Confirm', *args, **kwargs)

    def charge(self, *args, **kwargs):
        return self.buildQuery('Charge', *args, **kwargs)

    def addCustomer(self, *args, **kwargs):
        return self.buildQuery('AddCustomer', *args, **kwargs)

    def getCustomer(self, *args, **kwargs):
        return self.buildQuery('GetCustomer', *args, **kwargs)

    def removeCustomer(self, *args, **kwargs):
        return self.buildQuery('RemoveCustomer', *args, **kwargs)

    def getCardList(self, *args, **kwargs):
        return self.buildQuery('GetCardList', *args, **kwargs)

    def removeCard(self, *args, **kwargs):
        return self.buildQuery('RemoveCard', *args, **kwargs)

    def addCard(self, *args, **kwargs):
        return self.buildQuery('AddCard', *args, **kwargs)

    def attachCard(self, *args, **kwargs):
        return self.buildQuery('AttachCard', *args, **kwargs)
    
    def finishAuthorize(self, *args, **kwargs):
        return self.buildQuery('FinishAuthorize', *args, **kwargs)

    def cancel(self, *args, **kwargs):
        return self.buildQuery('Cancel', *args, **kwargs)

    def Check3DS(self, *args, **kwargs):
        return self.buildQuery('Submit3DSAuthorization', *args, **kwargs)

    def __init__(self, terminal_key, secret_key):
        self.api_url = 'https://securepay.tinkoff.ru/v2/'
        self.api_url_submit = 'https://securepay.tinkoff.ru/'
        self.terminal_key = terminal_key
        self.secret_key = secret_key

    def __get(self, name):
        if name == 'paymentId':
            return self.paymentId
        elif name == 'status':
            return self.status
        elif name == 'error':
            return self.error
        elif name == 'paymentUrl':
            return self.payment_url
        elif name == 'response':
            if self.response:
                return self.response
        else:
            if self.response:
                for k, v in self.response.items():
                    if name.lower() == k.lower():
                        return self.response[k]
            return False

    def _combineUrl(self, url, op):
        return url + op

    def buildQuery(self, op, *args, **kwargs):
        # print(kwargs)
        url = self.api_url
        if op == 'Submit3DSAuthorization': url = self.api_url_submit

        if kwargs is not None:
            if 'TerminalKey' not in kwargs: kwargs['TerminalKey'] = self.terminal_key
            if 'Token' not in kwargs: kwargs['Token'] = self._gen_token(**kwargs)
        # if 'CustomerKey' not in kwargs: kwargs['CustomerKey'] = kwargs['customer_key']
        url = self._combineUrl(url, op)
        return self._sendRequest(url, **kwargs)

    def _gen_token(self, *args, **kwargs):
        token = ''
        kwargs['Password'] = self.secret_key
        # сортировка по ключам
        lkwargs = sorted(kwargs.items(), key=lambda x: x[0])
        for arg in lkwargs:
            if type(arg[1]) != dict:
                token += arg[1]
        token = sha256(token.encode('utf-8')).hexdigest()
        return token

    def _sendRequest(self, url, *args, **kwargs):
        error = ''
        headers = {'Content-Type': 'application/json'}
        r = requests.post(url, data=json.dumps(kwargs), headers=headers)
        return r


