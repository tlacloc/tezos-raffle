import smartpy as sp

class LottoErrorMessage:
    PREFIX = "LOTTO_"
    INCORRECT_PURCHASE_VALUE = "{}INCORRECT_PURCHASE_VALUE".format(PREFIX)
    INSUFFICIENT_BALANCE = "{}INSUFFICIENT_BALANCE".format(PREFIX)
    NOT_OWNER = "{}NOT_OWNER".format(PREFIX)

class Lotto(sp.Contract):
    def __init__(self, admin):
        self.init(
            balance = sp.mutez(0),
            current_users = sp.map(tkey = sp.TNat, tvalue = sp.TAddress),
            ticket_price = sp.mutez(10000),
            lottery_batch = sp.nat(5),
            administrator = admin,
            active_tickets = sp.nat(0),
            last_winner = admin
            )

    def is_administrator(self, sender):
        return sender == self.data.administrator

    def reset_lottery(self):
        self.data.active_tickets = 0
        self.data.current_users = sp.map(l = {}, tkey = sp.TNat, tvalue = sp.TAddress)

    def set_winner(self):
        number = self.quazyrandomNat()
        self.data.last_winner = self.data.current_users[number]
        winer_cut = sp.local('winner_cut', sp.split_tokens(self.data.balance, 2, 5))
        sp.send(self.data.last_winner, winer_cut.value)
        self.data.balance -= winer_cut.value

    def quazyrandomNat(self):
        seed = sp.local('seed', sp.nat(0))
        seed.value = sp.as_nat(sp.timestamp_from_utc_now() - sp.timestamp(200))
        seed.value = (seed.value % sp.as_nat(self.data.lottery_batch - 1))
        return seed.value

    def store_ticket_value(self, number_of_tickets, user_pkh):
        sp.for i in sp.range(0, number_of_tickets):
            self.data.current_users[self.data.active_tickets] = user_pkh
            self.data.active_tickets += 1

    def available_tickets(self, quantity):
        buyable_tickets = sp.local('buyable_tickets', sp.nat(0))
        sp.if ((self.data.active_tickets + quantity) <= self.data.lottery_batch):
            buyable_tickets.value = quantity
        sp.else:
            buyable_tickets.value = sp.as_nat(self.data.lottery_batch - self.data.active_tickets)
        return buyable_tickets.value
            

    @sp.entry_point
    def set_price(self, params):
        sp.verify(self.is_administrator(sp.sender), message = LottoErrorMessage.NOT_OWNER)
        self.data.ticket_price = params

    @sp.entry_point
    def set_lottery_batch(self, params):
        sp.verify(self.is_administrator(sp.sender), message = LottoErrorMessage.NOT_OWNER)
        self.data.lottery_batch = params

    @sp.entry_point
    def buy_ticket(self, params):

        sp.verify(params.quantity > 0, LottoErrorMessage.INCORRECT_PURCHASE_VALUE)
        purchaseable_tickets = self.available_tickets(params.quantity)

        total_cost = sp.utils.mutez_to_nat(self.data.ticket_price) * purchaseable_tickets
        total_cost = sp.utils.nat_to_mutez(total_cost)
        sp.verify(sp.utils.mutez_to_nat(sp.amount) >= sp.utils.mutez_to_nat(total_cost), LottoErrorMessage.INSUFFICIENT_BALANCE)

        self.store_ticket_value(purchaseable_tickets, sp.sender)
        
        sp.if (total_cost < sp.amount):
            sp.send(sp.sender, sp.amount - total_cost)

        self.data.balance += total_cost

        sp.if (self.data.active_tickets == self.data.lottery_batch):
            self.set_winner()
            self.reset_lottery()



################################################                   
#        TESTS AND COMPILATION TARGET
################################################
+
if "templates" not in __name__:
    @sp.add_test(name = "Lotto Lottery")
    def test():
        scenario = sp.test_scenario()
        scenario.h1("Lottery")

        scenario.table_of_contents()
        
        scenario.h2("Accounts")
        admin = sp.test_account("admin")
        alice = sp.test_account("Alice")
        bob = sp.test_account("Bob")
        tomas = sp.test_account("Tomas")
        pedro = sp.test_account("Pedro")

        scenario.show([alice, bob, tomas, pedro])
        
        scenario.h2("Lottery Contract")
        
        c1 = Lotto(
            admin = admin.address)
        
        scenario += c1

        scenario.h2("Set ticket price")
        scenario += c1.set_price(sp.mutez(10)).run(sender = alice, valid = False)
        scenario += c1.set_price(sp.mutez(10)).run(sender = admin)

        scenario.h2("Set lottery batch")
        scenario += c1.set_lottery_batch(sp.nat(5)).run(sender = alice, valid = False)
        scenario += c1.set_lottery_batch(sp.nat(10)).run(sender = admin)

        scenario.h2("Purchace ticket")
        scenario += c1.buy_ticket(quantity = 1).run(sender = alice, amount = sp.mutez(0), valid = False)
        scenario += c1.buy_ticket(quantity = 1).run(sender = alice, amount = sp.mutez(10))
        scenario += c1.buy_ticket(quantity = 1).run(sender = bob, amount = sp.mutez(11))

        scenario += c1.buy_ticket(quantity = 3).run(sender = alice, amount = sp.mutez(0), valid = False)
        scenario += c1.buy_ticket(quantity = 3).run(sender = alice, amount = sp.mutez(30))
        scenario += c1.buy_ticket(quantity = 3).run(sender = bob, amount = sp.mutez(323))

        scenario += c1.buy_ticket(quantity = 1).run(sender = tomas, amount = sp.mutez(33))
        scenario += c1.buy_ticket(quantity = 3).run(sender = pedro, amount = sp.mutez(33))

        scenario.h3('Final Contract Balance')
        
        scenario.show(c1.balance)
        scenario.show(c1.data)

        scenario.h3('Users balance')

        scenario.show([alice, bob, tomas, pedro])

    sp.add_compilation_target("compilation", Lotto(
            admin = sp.address('tz1WbaFu1621EAx9bq5qv22RKUG1RAQqusSL'))
    )