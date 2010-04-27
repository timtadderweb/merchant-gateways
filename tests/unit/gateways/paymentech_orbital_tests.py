
from merchant_gateways.billing.gateways.paymentech_orbital import PaymentechOrbital
from merchant_gateways.billing.credit_card import CreditCard
from merchant_gateways.tests.test_helper import *
from pprint import pprint

class PaymentechOrbitalTests(MerchantGatewaysTestSuite,
                             MerchantGatewaysTestSuite.CommonTests):

    def gateway_type(self):
        return PaymentechOrbital

    def mock_webservice(self, response):

        self.options['billing_address'] = {}  #  TODO  put something in there, throw an error if it ain't there
        self.mock_post_webservice(response)

    def assert_successful_authorization(self):
        #  TODO  de-cybersource all this
        order_id = str(self.options['order_id'])  #  TODO  put something in options
#        requestID = '1842651133440156177166'
#        requestToken = 'AP4JY+Or4xRonEAOERAyMzQzOTEzMEM0MFZaNUZCBgDH3fgJ8AEGAMfd+AnwAwzRpAAA7RT/'
#        authorization = ';'.join([order_id, requestID, requestToken])
        self.assert_equal('4A785F5106CCDC41A936BFF628BF73036FEC5401', self.response.authorization) # TODO  why not from <c:authorizationCode>004542</c:authorizationCode> ?
        self.assert_equal('Approved', self.gateway.message)
        assert self.response.success

    def assert_failed_authorization(self):
        self.assert_none(self.response.params['TxRefNum'])
         #  TODO  assert the message
        self.assert_none(self.response.fraud_review)

        reference = { 'AVSRespCode': None,
                      'AccountNum': None,
                      'ApprovalStatus': None,
                      'AuthCode': None,
                      'CAVVRespCode': None,  #  TODO  diff between CAVV and CVV2??
                      'CVV2RespCode': None,
                      'CardBrand': None,
                      'CustomerName': None,
                      'CustomerProfileMessage': 'Profile: Unable to Perform Profile Transaction. The Associated Transaction Failed. ',
                      'CustomerRefNum': None,
                      'HostAVSRespCode': None,
                      'HostCVV2RespCode': None,
                      'HostRespCode': None,
                      'IndustryType': None,
                      'MerchantID': None,
                      'MessageType': None,
                      'OrderID': None,
                      'ProcStatus': '841',
                      'ProfileProcStatus': '9576',
                      'RecurringAdviceCd': None,
                      'RespCode': None,
                      'RespMsg': None,
                      'RespTime': None,
                      'StatusMsg': 'Error validating card/account number range',
                      'TerminalID': None,
                      'TxRefIdx': None,
                      'TxRefNum': None }

        self.assert_match_hash(self.response.params, reference)
        self.assert_equal('Error validating card/account number range', self.response.message)

    def assert_successful_purchase(self):
        '''TODO self.assert_equal( 'Successful transaction', self.response.message )'''

    def test_build_request(self):
        #  TODO  de-cybersource me
        reference = '''<?xml version="1.0" encoding="UTF-8"?>
            <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
              <s:Header>
                <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" s:mustUnderstand="1">
                  <wsse:UsernameToken>
                    <wsse:Username>l</wsse:Username>
                    <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">p</wsse:Password>
                  </wsse:UsernameToken>
                </wsse:Security>
              </s:Header>
              <s:Body xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <requestMessage xmlns="urn:schemas-cybersource-com:transaction-data-1.32">
                  <merchantID>l</merchantID>
                  <merchantReferenceCode>1000</merchantReferenceCode>
                  <clientLibrary>Ruby Active Merchant</clientLibrary>
                  <clientLibraryVersion>1.0</clientLibraryVersion>
                  <clientEnvironment>Linux</clientEnvironment>
                    Aparecium
                </requestMessage>
              </s:Body>
            </s:Envelope>
            '''

        sample = self.gateway.build_request('Aparecium')  #  TODO  as usual, options!
        self.assert_match_xml(reference, sample)

    def parsed_authentication_response(self):
        return dict(
            AccountNum='5454545454545454',
            ApprovalStatus='1',
            AuthCode='tst554',
            AVSRespCode='B ',
            CardBrand='MC',
            CAVVRespCode=None,
            CustomerName='JOE SMITH',
            CustomerProfileMessage='Profile Created',  #  TODO  use this?
            CustomerRefNum='2145108',
            CVV2RespCode='M',
            HostAVSRespCode='I3',
            HostCVV2RespCode='M',
            HostRespCode='100',
            IndustryType=None,
            MerchantID='000000',
            MessageType='AC',
            OrderID='1',
            ProcStatus='0',
            ProfileProcStatus='0',
            RecurringAdviceCd=None,
            RespCode='00',
            RespMsg=None,
            RespTime='121825',
            StatusMsg='Approved',
            TerminalID='000',
            TxRefIdx='1',
            TxRefNum='4A785F5106CCDC41A936BFF628BF73036FEC5401',
        )

    def test_parse(self):
        soap = self.successful_authorization_response()
        sample = self.gateway.parse(soap)
        reference = self.parsed_authentication_response()
        self.assert_match_hash(reference, sample)

    def test_parse_purchase_response(self):
        soap = self.successful_purchase_response()
        sample = self.gateway.parse(soap)
        return # TODO
        self.assert_equal(sample['cvCode'], 'M')
        self.assert_equal(sample['cvCodeRaw'], 'M')  #  TODO  what to do with the raw code?

    def test_setup_address_hash(self):  #  TODO  everyone should fixup like these (Payflow does it a different way)
        g = self.gateway
        self.assert_equal({}, g.setup_address_hash()['billing_address'])
        addy = dict(yo=42)
        self.assert_equal(addy, g.setup_address_hash(billing_address=addy)['billing_address'])
        self.assert_equal(addy, g.setup_address_hash(address=addy)['billing_address'])
        self.assert_equal({}, g.setup_address_hash()['shipping_address'])
        self.assert_equal(addy, g.setup_address_hash(shipping_address=addy)['shipping_address'])

    #  TODO  always credit_card never creditcard

    def test_build_auth_request(self):
        self.money = Decimal('100.00')

        self.options = {
            'order_id': '1',
            'description': 'Time-Turner',
            'email': 'hgranger@hogwarts.edu',
            'customer': '947',    #  TODO  test this going through
            'ip': '192.168.1.1',  #  TODO  test this going through
        }

        billing_address = {
            'address1': '444 Main St.',
            'address2': 'Apt 2',
            'company': 'ACME Software',  #  TODO  where's the love for the company?
            'phone': '222-222-2222',      #  TODO  where the phone number goes?
            'zip': '77777',
            'city': 'Dallas',
            'country': 'USA',
            'state': 'TX'
        }

        self.options['billing_address'] = billing_address
        self.options['login'] = 'Triwizard'  #  TODO  is the one true standard interface "login" or "username"
        self.options['password'] = 'Tournament'

        message = self.gateway.build_auth_request(self.money, self.credit_card, **self.options)

#        {'start_month': None, 'verification_value': None, 'start_year': None, 'card_type': 'v', 'issue_number': None, }

        # TODO enforce <?xml version="1.0" encoding="UTF-8"?> tags??
        #  ERGO  configure the sample correctly at error time

        assert   12 == self.credit_card.month
        assert 2090 == self.credit_card.year

        self.assert_xml(message, lambda x:
                             x.Request(
                                 x.NewOrder(
                        x.OrbitalConnectionUsername('Triwizard'),
                        x.OrbitalConnectionPassword('Tournament'),
                        x.IndustryType('EC'),
                        x.MessageType('A'),
                        x.BIN('1'),
                        x.MerchantID('1'),   #  TODO  configure all these so we don't need to think about them
                        x.TerminalID('1'),
                        x.CardBrand(''),
                        x.AccountNum('4242424242424242'),
                        x.Exp('1290'),
                        x.CurrencyCode('840'),
                        x.CurrencyExponent('2'),
                        x.CardSecValInd('1'),
                        x.CardSecVal(self.credit_card.verification_value),
                        x.AVSzip(billing_address['zip']),
                        x.AVSaddress1(billing_address['address1']),
                        x.AVSaddress2(billing_address['address2']),
                        x.AVScity(billing_address['city']),
                        x.AVSstate(billing_address['state']),
                        x.AVSphoneNum(billing_address['phone']),
                        x.AVSname(self.credit_card.first_name + ' ' + self.credit_card.last_name), #  TODO is this really the first & last names??
                        x.AVScountryCode('840'),
                        x.CustomerProfileFromOrderInd('A'),
                        x.CustomerProfileOrderOverrideInd('NO'),
                        x.OrderID(''),
                        x.Amount('100.00')
                                 )
                             )
                   )

        # TODO default_dict should expose all members as read-only data values

    def test_build_auth_request_without_street2(self):
        self.money = Decimal('2.00')

        self.options = {
            'order_id': '1',
            'description': 'Time-Turner',  # TODO  take as much of this out as possible
            'email': 'hgranger@hogwarts.edu',
            'customer': '947',
            'ip': '192.168.1.1',
        }

        billing_address = {
            'address1': '444 Main St.',
            'company': 'ACME Software',  #  TODO  where's the love for the company?
            'phone': '222-222-2222',      #  TODO  where the phone number goes?
            'zip': '77777',
            'city': 'Dallas',
            'country': 'USA',
            'state': 'TX'
        }

        self.options['billing_address'] = billing_address

        message = self.gateway.build_auth_request(self.money, self.credit_card, **self.options)

        #  TODO  default not to USD

        # self.assert_('<street2></street2>' in message)  #  TODO  assert_contains

    def test_(self):
        amount = 100   #  TODO  de-cybersource this

        credit_card = CreditCard( verification_value="123",
                                  number="4111111111111111",
                                  year=2011,
                                  card_type="visa",
                                  month=9,
                                  last_name="Longsen", first_name="Longbob")  #  TODO  'harry potter'

        options = dict( email="someguy1232@fakeemail.net", order_id="1000", shipping_address={}, currency="USD",
                        billing_address=dict(country="Canada", address1="1234 My Street", phone="(555)555-5555",
                                             address2="Apt 1", zip="K1C2N6", company="Widgets Inc", city="Ottawa",
                                             state="ON"))   #  TODO  de-cybersource this

        reference = '''<billTo>
                              <firstName>Longbob</firstName>
                              <lastName>Longsen</lastName>
                              <street1>1234 My Street</street1>
                              <street2>Apt 1</street2>
                              <city>Ottawa</city>
                              <state>ON</state>
                              <postalCode>K1C2N6</postalCode>
                              <country>Canada</country>
                              <email>someguy1232@fakeemail.net</email>
                            </billTo>
                            <purchaseTotals>
                              <currency>USD</currency>
                              <grandTotalAmount>1.00</grandTotalAmount>
                            </purchaseTotals>
                            <card>
                              <accountNumber>4111111111111111</accountNumber>
                              <expirationMonth>09</expirationMonth>
                              <expirationYear>2011</expirationYear>
                              <cvNumber>123</cvNumber>
                              <cardType>001</cardType>
                            </card>
                            <ccAuthService run="true" />
                            <ccCaptureService run="true" />
                            <businessRules></businessRules>'''    #  TODO  de-cybersource this

        sample = self.gateway.build_purchase_request(amount, credit_card, **options)
        # TODO self.assert_xml_match(reference, sample)

    #  ERGO  script that coverts XML to its ElementMaker notation

    def successful_authorization_response(self):
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
<NewOrderResp>
  <IndustryType/>
  <MessageType>AC</MessageType>
  <MerchantID>000000</MerchantID>
  <TerminalID>000</TerminalID>
  <CardBrand>MC</CardBrand>
  <AccountNum>5454545454545454</AccountNum>
  <OrderID>1</OrderID>
  <TxRefNum>4A785F5106CCDC41A936BFF628BF73036FEC5401</TxRefNum>
  <TxRefIdx>1</TxRefIdx>
  <ProcStatus>0</ProcStatus>
  <ApprovalStatus>1</ApprovalStatus>
  <RespCode>00</RespCode>
  <AVSRespCode>B </AVSRespCode>
  <CVV2RespCode>M</CVV2RespCode>
  <AuthCode>tst554</AuthCode>
  <RecurringAdviceCd/>
  <CAVVRespCode/>
  <StatusMsg>Approved</StatusMsg>
  <RespMsg/>
  <HostRespCode>100</HostRespCode>
  <HostAVSRespCode>I3</HostAVSRespCode>
  <HostCVV2RespCode>M</HostCVV2RespCode>
  <CustomerRefNum>2145108</CustomerRefNum>
  <CustomerName>JOE SMITH</CustomerName>
  <ProfileProcStatus>0</ProfileProcStatus>
  <CustomerProfileMessage>Profile Created</CustomerProfileMessage>
  <RespTime>121825</RespTime>
</NewOrderResp>
</Response>
'''

    def failed_authorization_response(self):
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
<QuickResp>
  <ProcStatus>841</ProcStatus>
  <StatusMsg>Error validating card/account number range</StatusMsg>
  <CustomerBin></CustomerBin>
  <CustomerMerchantID></CustomerMerchantID>
  <CustomerName></CustomerName>
  <CustomerRefNum></CustomerRefNum>
  <CustomerProfileAction></CustomerProfileAction>
  <ProfileProcStatus>9576</ProfileProcStatus>
  <CustomerProfileMessage>Profile: Unable to Perform Profile Transaction. The Associated Transaction Failed. </CustomerProfileMessage>
  <CustomerAddress1></CustomerAddress1>
  <CustomerAddress2></CustomerAddress2>
  <CustomerCity></CustomerCity>
  <CustomerState></CustomerState>
  <CustomerZIP></CustomerZIP>
  <CustomerEmail></CustomerEmail>
  <CustomerPhone></CustomerPhone>
  <CustomerProfileOrderOverrideInd></CustomerProfileOrderOverrideInd>
  <OrderDefaultDescription></OrderDefaultDescription>
  <OrderDefaultAmount></OrderDefaultAmount>
  <CustomerAccountType></CustomerAccountType>
  <CCAccountNum></CCAccountNum>
  <CCExpireDate></CCExpireDate>
  <ECPAccountDDA></ECPAccountDDA>
  <ECPAccountType></ECPAccountType>
  <ECPAccountRT></ECPAccountRT>
  <ECPBankPmtDlv></ECPBankPmtDlv>
  <SwitchSoloStartDate></SwitchSoloStartDate>
  <SwitchSoloIssueNum></SwitchSoloIssueNum>
</QuickResp>
</Response>'''

        #  ERGO  complain that 'private' in a test case is irrational...

    def successful_purchase_response(self):  #  TODO  de-cybersource this
        return '''<?xml version="1.0" encoding="utf-8"?>
                  <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                    <soap:Header>
                      <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
                        <wsu:Timestamp xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
                        wsu:Id="Timestamp-2636690">
                          <wsu:Created>2008-01-15T21:42:03.343Z</wsu:Created>
                        </wsu:Timestamp>
                      </wsse:Security>
                    </soap:Header>
                    <soap:Body>
                      <c:replyMessage xmlns:c="urn:schemas-cybersource-com:transaction-data-1.26">
                        <c:merchantReferenceCode>b0a6cf9aa07f1a8495f89c364bbd6a9a</c:merchantReferenceCode>
                        <c:requestID>2004333231260008401927</c:requestID>
                        <c:decision>ACCEPT</c:decision>
                        <c:reasonCode>100</c:reasonCode>
                        <c:requestToken>Afvvj7Ke2Fmsbq0wHFE2sM6R4GAptYZ0jwPSA+R9PhkyhFTb0KRjoE4+ynthZrG6tMBwjAtT</c:requestToken>
                        <c:purchaseTotals>
                          <c:currency>USD</c:currency>
                        </c:purchaseTotals>
                        <c:ccAuthReply>
                          <c:reasonCode>100</c:reasonCode>
                          <c:amount>1.00</c:amount>
                          <c:authorizationCode>123456</c:authorizationCode>
                          <c:avsCode>Y</c:avsCode>
                          <c:avsCodeRaw>Y</c:avsCodeRaw>
                          <c:cvCode>M</c:cvCode>
                          <c:cvCodeRaw>M</c:cvCodeRaw>
                          <c:authorizedDateTime>2008-01-15T21:42:03Z</c:authorizedDateTime>
                          <c:processorResponse>00</c:processorResponse>
                          <c:authFactorCode>U</c:authFactorCode>
                        </c:ccAuthReply>
                      </c:replyMessage>
                    </soap:Body>
                  </soap:Envelope>'''

# ERGO  put us into the test report system and see what we look like!
