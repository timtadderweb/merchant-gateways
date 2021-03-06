import re

from gateway import Gateway, default_dict
from merchant_gateways import MerchantGatewayError
from merchant_gateways.billing import response

from merchant_gateways.billing.common import xStr, ElementMaker, gencode
XML = ElementMaker()

# TODO use this      XMLNS = 'http://www.paypal.com/XMLPay'
# TODO  actually write a real post_webservice
# TODO  advise NB that active_merchant has braintree - of course!

def strip_to_numbers(number):
    """ remove spaces from the number """
    return re.sub('[^0-9]+', '', number)

class Payflow(Gateway):
    CARD_STORE = True
    TEST_URL = 'https://pilot-payflowpro.paypal.com'
    LIVE_URL = 'https://payflowpro.paypal.com'

    def authorize(self, money, credit_card, card_store_id=None, **options):  #  TODO  rename money to amount, everywhere
        credit_card_or_reference = credit_card or card_store_id
        request = self.build_sale_or_authorization_request('authorization', money, credit_card_or_reference, **options)
        return self.commit(request)

    def build_sale_or_authorization_request(self, action, money, credit_card_or_reference, **options):  # TODO  tdd each arg
        if isinstance(credit_card_or_reference, basestring):
            return self.build_reference_sale_or_authorization_request(action, money, credit_card_or_reference, **options)
        else:
            return self.build_credit_card_request(action, money, credit_card_or_reference, **options)

    def commit(self, request_body, request_type = None):
        request = self.build_request(request_body, request_type)
        headers = self.build_headers(len(request))  #  TODO  glyph length or byte length???

        url = (self.gateway_mode == 'live') and self.LIVE_URL or self.TEST_URL
        result = self.parse(self.post_webservice(url, request, headers))

        # self.result = parse(ssl_post(test? ? TEST_URL : LIVE_URL, request, headers))'''

        passed = result['Result'] == '0'
        message = passed and 'Approved' or 'Declined'

        response = Payflow.Response( passed, message, None, # TODO response[:result] == "0", response[:message], response,
            is_test=self.is_test,
            authorization=result.get('PNRef', result.get('RPRef', None)),  #  TODO  test the RPRef
            cvv_result = CVV_CODE[result.get('CvResult', None)],  #  TODO  default_dict to the rescue!
            avs_result = result.get('AvsResult', None),
            card_store_id = result.get('PNRef', None),
            )  #  TODO  stash the response in self.response
        response.result = result
        return response

    def purchase(self, money, credit_card, card_store_id=None, **options):  #  TODO every purchase can work on a cc or ref!
        credit_card_or_reference = credit_card or card_store_id
        self.message = self.build_sale_or_authorization_request('purchase', money, credit_card_or_reference, **options)
        return self.commit(self.message)  #  TODO  test we return something

    def build_headers(self, content_length):  #  TODO doesn't an HTTP library take care of this for us?
        return {
          "Content-Type" : "text/xml",
          "Content-Length" : str(content_length),
          "X-VPS-Client-Timeout" : '30',  #  TODO  bfd?!
          "X-VPS-VIT-Integration-Product" : "TODO what's my name",
          "X-VPS-VIT-Runtime-Version" : '4.2',  #  TODO  what's my version?
          "X-VPS-Request-ID" : gencode(),
        }

    def build_request(self, request_body, request_type=None):  # TODO  what's the request_type for?
        template = '''<?xml version="1.0" encoding="UTF-8"?>
<XMLPayRequest Timeout="30" version="2.1"
xmlns="http://www.paypal.com/XMLPay">
  <RequestData>
    <Vendor>%(vendor)s</Vendor>
    <Partner>%(partner)s</Partner>
    <Transactions>
      <Transaction>
        <Verbosity>MEDIUM</Verbosity>
        %(request_body)s
      </Transaction>
    </Transactions>
  </RequestData>
  <RequestAuth>
    <UserPass>
      <User>%(user)s</User>
      <Password>%(password)s</Password>
    </UserPass>
  </RequestAuth>
</XMLPayRequest>
'''  #  TODO  vary all this data
        info = self.options.copy()
        info.setdefault('vendor', 'LOGIN')
        info.setdefault('user', 'LOGIN')
        info.setdefault('partner', 'PayPal')
        info.setdefault('password', 'PASSWORD')
        info['request_body'] = request_body
        return template % info

    def build_reference_sale_or_authorization_request(self, action, money, reference, **options): #TODO tdd this
        transaction_type = TRANSACTIONS[action]
        formatted_amount = '%.2f' % money.amount  #  TODO  rename to money; merge with grandTotalAmount system
        return xStr(
            XML(transaction_type,
                XML.PayData(
                    XML.Invoice(
                        XML.TotalAmt(formatted_amount, Currency=str(money.currency.code))
                    ),
                    XML.Tender(
                        XML.Card(
                            XML.ExtData(Name='ORIGID', Value=reference)
                        )
                    )
                )
            )
        )

    def build_credit_card_request(self, action, money, credit_card, **options):
        transaction_type = TRANSACTIONS[action]
          # amount=self.options['amount'] ) # TODO all options in options - no exceptions
        formatted_amount = '%.2f' % money.amount  #  TODO  rename to money; merge with grandTotalAmount system
        bill_to_address = options.get('address', {})  #  TODO  billing_address etc???

        request = XML(transaction_type,
                    XML.PayData(
                      XML.Invoice(
                          self.add_address('BillTo', **bill_to_address),
                          XML.TotalAmt(formatted_amount, Currency=str(money.currency.code))
                      ),
                      XML.Tender(
                          self.add_credit_card(credit_card)
                      )))
        return xStr(request)

    def add_address(self, _where_to, **address):
        if not address:  return ''
        address = default_dict(address)
        elements = list()
        elements.append(XML.Name(address['name']))
        if address.get('phone','').strip():
            #xxx-xxx-xxxx (US numbers) +xxxxxxxxxxx (international numbers)
            phone = strip_to_numbers(address['phone'])
            if len(phone) == 10 and address['country'] == 'US':
                phone = '%s-%s-%s' % (phone[0:3], phone[3:6], phone[6:10])
            else:
                phone = '+'+phone
            elements.append(XML.Phone(phone))
        elements.append(XML.Address(
                              XML.Street(address['address1']),
                              XML.City(address['city']),
                              XML.State(address['state']),
                              XML.Country(address['country']),
                              XML.Zip(address['zip'])))
        return XML(_where_to, *elements)

    class Response(response.Response):
        def avs_result(self):
            'TODO'
          #  print self.__dict__

# TODO      def profile_id
#        @params['profile_id']
 #     end

#      def payment_history
#        @payment_history ||= @params['rp_payment_result'].collect{ |result| result.stringify_keys } rescue []
#      end

    def parse(self, data):  #  TODO  use self.message
        response = {}
        from lxml import etree
        xml = etree.XML(data)
        namespaces={'paypal':'http://www.paypal.com/XMLPay'}
        root = xml.xpath('..//paypal:TransactionResult', namespaces=namespaces)[0]
        for node in root.xpath('*', namespace='paypal', namespaces=namespaces):
            response[node.tag.split('}')[-1]] = node.text
        if response.get('Result') != '0':
            raise MerchantGatewayError(response.get('Message', 'No error message given'), response)
        '''
        root = REXML::XPath.first(xml, "//ResponseData")

        # REXML::XPath in Ruby 1.8.6 is now unable to match nodes based on their attributes
        tx_result = REXML::XPath.first(root, "//TransactionResult")

        if tx_result && tx_result.attributes['Duplicate'] == "true"
          response[:duplicate] = true
        end

        root.elements.to_a.each do |node|
          parse_element(response, node)  #  TODO  so what?
        end'''

        return response

    def add_credit_card(self, credit_card):

        fields = [  XML.CardType(self.credit_card_type(credit_card)),  #  TODO  test all types
                    XML.CardNum(credit_card.number),
                    XML.ExpDate(self.expdate(credit_card)),
                    XML.NameOnCard(credit_card.name()),
                    XML.CVNum(credit_card.verification_value), # TODO if credit_card.verification_value?
                    XML.ExtData(Name='LASTNAME', Value=credit_card.last_name) ]

        if self.requires_start_date_or_issue_number(credit_card):  #  TODO  TDD
            issue = format(credit_card.issue_number, two_digits=True)
            fields.append(XML.ExtData(Name='CardIssue', Value=issue)) # TODO  unless credit_card.start_month.blank? || credit_card.start_year.blank?

                #  TODO  format(credit_card.issue_number, :two_digits))

        return XML.Card(*fields)
#          xml.tag! 'ExpDate', expdate(credit_card)
#          xml.tag! 'NameOnCard', credit_card.first_name
#          xml.tag! 'CVNum', credit_card.verification_value if credit_card.verification_value?
#
#          if requires_start_date_or_issue_number?(credit_card)
#            xml.tag!('ExtData', 'Name' => 'CardStart', 'Value' => startdate(credit_card)) unless credit_card.start_month.blank? || credit_card.start_year.blank?
#            xml.tag!('ExtData', 'Name' => 'CardIssue', 'Value' => format(credit_card.issue_number, :two_digits)) unless credit_card.issue_number.blank?
#          end
#          xml.tag! 'ExtData', 'Name' => 'LASTNAME', 'Value' =>  credit_card.last_name

    def credit_card_type(self, credit_card):
        if self.card_brand(credit_card) in [None, '']:  return ''
        return CARD_MAPPING.get(self.card_brand(credit_card), '')

    def expdate(self, credit_card):
        year  = "%.4i" % credit_card.year
        month = "%.2i" % credit_card.month
        return year + month

    def build_reference_request(self, action, money, authorization):
        return xStr(
            XML(TRANSACTIONS[action],
                XML.PNRef(authorization),
                *self.invoice_total_amt(money)
                )
            )

    def void(self, authorization):
        self.request = self.build_reference_request('void', None, authorization)
        return self.commit(self.request)

    def invoice_total_amt(self, money):
        if not money:  return []

        return [
                XML.Invoice(
                        XML.TotalAmt( '%.2f' % money.amount, #  TODO currency-specific template!
                                      Currency=str(money.currency.code) ) )
        ]

    def credit(self, money, identification_or_credit_card):
        if True:  # TODO identification_or_credit_card.is_a?(String)
          # Perform referenced credit
          request = self.build_reference_request('credit', money, identification_or_credit_card)
        else:
          # Perform non-referenced credit
          '# TODO request = build_credit_card_request(:credit, money, identification_or_credit_card, options)'

        return self.commit(request)

    def capture(self, money, authorization, **options):
        request = self.build_reference_request('capture', money, authorization)
        return self.commit(request)

'''      include PayflowCommonAPI

      RECURRING_ACTIONS = Set.new([:add, :modify, :cancel, :inquiry, :reactivate, :payment])

      self.supported_cardtypes = [:visa, :master, :american_express, :jcb, :discover, :diners_club]
      self.homepage_url = 'https://www.paypal.com/cgi-bin/webscr?cmd=_payflow-pro-overview-outside'
      self.display_name = 'PayPal Payflow Pro'

      def purchase(money, credit_card_or_reference, options = {})
        request = build_sale_or_authorization_request(:purchase, money, credit_card_or_reference, options)

        commit(request)
      end

      def credit(money, identification_or_credit_card, options = {})
        if identification_or_credit_card.is_a?(String)
          # Perform referenced credit
          request = build_reference_request(:credit, money, identification_or_credit_card, options)
        else
          # Perform non-referenced credit
          request = build_credit_card_request(:credit, money, identification_or_credit_card, options)
        end

        commit(request)
      end

      # Adds or modifies a recurring Payflow profile.  See the Payflow Pro Recurring Billing Guide for more details:
      # https://www.paypal.com/en_US/pdf/PayflowPro_RecurringBilling_Guide.pdf
      #
      # Several options are available to customize the recurring profile:
      #
      # * <tt>profile_id</tt> - is only required for editing a recurring profile
      # * <tt>starting_at</tt> - takes a Date, Time, or string in mmddyyyy format. The date must be in the future.
      # * <tt>name</tt> - The name of the customer to be billed.  If not specified, the name from the credit card is used.
      # * <tt>periodicity</tt> - The frequency that the recurring payments will occur at.  Can be one of
      # :bimonthly, :monthly, :biweekly, :weekly, :yearly, :daily, :semimonthly, :quadweekly, :quarterly, :semiyearly
      # * <tt>payments</tt> - The term, or number of payments that will be made
      # * <tt>comment</tt> - A comment associated with the profile
      def recurring(money, credit_card, options = {})
        options[:name] = credit_card.name if options[:name].blank? && credit_card
        request = build_recurring_request(options[:profile_id] ? :modify : :add, money, options) do |xml|
          add_credit_card(xml, credit_card) if credit_card
        end
        commit(request, :recurring)
      end

      def void(authorization, options = {})
        request = build_reference_request(:void, nil, authorization, options)
        commit(request)
      end

      def cancel_recurring(profile_id)
        request = build_recurring_request(:cancel, 0, :profile_id => profile_id)
        commit(request, :recurring)
      end

      def recurring_inquiry(profile_id, options = {})
        request = build_recurring_request(:inquiry, nil, options.update( :profile_id => profile_id ))
        commit(request, :recurring)
      end

      def express
        @express ||= PayflowExpressGateway.new(@options)
      end

      private

      def build_reference_sale_or_authorization_request(action, money, reference, options)
        xml = Builder::XmlMarkup.new
        xml.tag! TRANSACTIONS[action] do
          xml.tag! 'PayData' do
            xml.tag! 'Invoice' do
              xml.tag! 'TotalAmt', amount(money), 'Currency' => options[:currency] || currency(money)
            end
            xml.tag! 'Tender' do
              xml.tag! 'Card' do
                xml.tag! 'ExtData', 'Name' => 'ORIGID', 'Value' =>  reference
              end
            end
          end
        end
        xml.target!
      end

      def build_credit_card_request(action, money, credit_card, options)
        xml = Builder::XmlMarkup.new
        xml.tag! TRANSACTIONS[action] do
          xml.tag! 'PayData' do
            xml.tag! 'Invoice' do
              xml.tag! 'CustIP', options[:ip] unless options[:ip].blank?
              xml.tag! 'InvNum', options[:order_id].to_s.gsub(/[^\w.]/, '') unless options[:order_id].blank?
              xml.tag! 'Description', options[:description] unless options[:description].blank?

              billing_address = options[:billing_address] || options[:address]
              add_address(xml, 'BillTo', billing_address, options) if billing_address
              add_address(xml, 'ShipTo', options[:shipping_address], options) if options[:shipping_address]

              xml.tag! 'TotalAmt', amount(money), 'Currency' => options[:currency] || currency(money)
            end

            xml.tag! 'Tender' do
              add_credit_card(xml, credit_card)
            end
          end
        end
        xml.target!
      end

      def add_credit_card(xml, credit_card)
        xml.tag! 'Card' do
          xml.tag! 'CardType', credit_card_type(credit_card)
          xml.tag! 'CardNum', credit_card.number
          xml.tag! 'ExpDate', expdate(credit_card)
          xml.tag! 'NameOnCard', credit_card.first_name
          xml.tag! 'CVNum', credit_card.verification_value if credit_card.verification_value?

          if requires_start_date_or_issue_number?(credit_card)
            xml.tag!('ExtData', 'Name' => 'CardStart', 'Value' => startdate(credit_card)) unless credit_card.start_month.blank? || credit_card.start_year.blank?
            xml.tag!('ExtData', 'Name' => 'CardIssue', 'Value' => format(credit_card.issue_number, :two_digits)) unless credit_card.issue_number.blank?
          end
          xml.tag! 'ExtData', 'Name' => 'LASTNAME', 'Value' =>  credit_card.last_name
        end
      end

      def credit_card_type(credit_card)
        return '' if card_brand(credit_card).blank?

        CARD_MAPPING[card_brand(credit_card).to_sym]
      end

      def startdate(creditcard)
        year  = format(creditcard.start_year, :two_digits)
        month = format(creditcard.start_month, :two_digits)

        "#{month}#{year}"
      end

      def build_recurring_request(action, money, options)
        unless RECURRING_ACTIONS.include?(action)
          raise StandardError, "Invalid Recurring Profile Action: #{action}"
        end

        xml = Builder::XmlMarkup.new
        xml.tag! 'RecurringProfiles' do
          xml.tag! 'RecurringProfile' do
            xml.tag! action.to_s.capitalize do
              unless [:cancel, :inquiry].include?(action)
                xml.tag! 'RPData' do
                  xml.tag! 'Name', options[:name] unless options[:name].nil?
                  xml.tag! 'TotalAmt', amount(money), 'Currency' => options[:currency] || currency(money)
                  xml.tag! 'PayPeriod', get_pay_period(options)
                  xml.tag! 'Term', options[:payments] unless options[:payments].nil?
                  xml.tag! 'Comment', options[:comment] unless options[:comment].nil?


                  if initial_tx = options[:initial_transaction]
                    requires!(initial_tx, [:type, :authorization, :purchase])
                    requires!(initial_tx, :amount) if initial_tx[:type] == :purchase

                    xml.tag! 'OptionalTrans', TRANSACTIONS[initial_tx[:type]]
                    xml.tag! 'OptionalTransAmt', amount(initial_tx[:amount]) unless initial_tx[:amount].blank?
                  end

                  xml.tag! 'Start', format_rp_date(options[:starting_at] || Date.today + 1 )
                  xml.tag! 'EMail', options[:email] unless options[:email].nil?

                  billing_address = options[:billing_address] || options[:address]
                  add_address(xml, 'BillTo', billing_address, options) if billing_address
                  add_address(xml, 'ShipTo', options[:shipping_address], options) if options[:shipping_address]
                end
                xml.tag! 'Tender' do
                  yield xml
                end
              end
              if action != :add
                xml.tag! "ProfileID", options[:profile_id]
              end
              if action == :inquiry
                xml.tag! "PaymentHistory", ( options[:history] ? 'Y' : 'N' )
              end
            end
          end
        end
      end

      def get_pay_period(options)
        requires!(options, [:periodicity, :bimonthly, :monthly, :biweekly, :weekly, :yearly, :daily, :semimonthly, :quadweekly, :quarterly, :semiyearly])
        case options[:periodicity]
          when :weekly then 'Weekly'
          when :biweekly then 'Bi-weekly'
          when :semimonthly then 'Semi-monthly'
          when :quadweekly then 'Every four weeks'
          when :monthly then 'Monthly'
          when :quarterly then 'Quarterly'
          when :semiyearly then 'Semi-yearly'
          when :yearly then 'Yearly'
        end
      end

      def format_rp_date(time)
        case time
          when Time, Date then time.strftime("%m%d%Y")
        else
          time.to_s
        end
      end


'''

TRANSACTIONS = dict(
        purchase       = 'Sale',
        authorization  = 'Authorization',
        capture        = 'Capture',
        void           = 'Void',
        credit         = 'Credit'
      )

CARD_MAPPING = dict(
        visa='Visa',
        master='MasterCard',
        discover='Discover',
        american_express='Amex',
        jcb='JCB',
        diners_club='DinersClub',
        switch='Switch',
        solo='Solo',
        v='Visa',
        m='MasterCard',
        d='Discover',
        ax='Amex',
        dx='DinersClub',
        sw='Switch',
        s='Solo',
      )

CVV_CODE = {
        'Match'                 : 'M',
        'No Match'              : 'N',
        'Service Not Available' : 'U',
        'Service not Requested' : 'P',
        None: None
      }  #  TODO  test all these!

def format(number, **options):  #  TODO  move to credit_card_formatting!
    if number in [None, '']:  return ''
    last = ('000000000000000000000000000000' + str(number))[-2:]
    return last

