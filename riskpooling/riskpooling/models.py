from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
import random
from django.db import models as djmodels

author = 'Scott Claessens'

doc = """Risk-pooling game"""


class Constants(BaseConstants):
    name_in_url = 'riskpooling'
    players_per_group = 3
    num_rounds = 10


class Subsession(BaseSubsession):
    def creating_session(self):
        for p in self.get_players():
            p.participant.vars['herd_size'] = c(self.session.config['initialherd'])
            p.participant.vars['under_minimum_years_left'] = self.session.config['years_before_death']
            p.participant.vars['dead'] = False



class Group(BaseGroup):
    def no_requests(self):
        n = 0
        for p in self.get_players():
            if p.request is True:
                n += 1
        if n == 0:
            self.norequests = True
        else:
            self.norequests = False

    norequests = models.BooleanField()


class Player(BasePlayer):
    def set_under_minimum_years_left(self):
        self.under_minimum_years_left = self.participant.vars['under_minimum_years_left']

    def set_growth(self):
        self.herd_size_initial = self.participant.vars['herd_size']
        growth_rate = random.gauss(self.session.config['growth_rate_mean'], self.session.config['growth_rate_sd'])
        self.participant.vars['herd_size'] = self.participant.vars['herd_size'] + (growth_rate * self.participant.vars['herd_size'])
        if self.participant.vars['herd_size'] > c(self.session.config['maxherd']):
            self.participant.vars['herd_size'] = c(self.session.config['maxherd'])
        self.herd_size_after_growth = self.participant.vars['herd_size']
        if self.herd_size_after_growth < c(self.session.config['minherd']):
            self.under_minimum = True
        else:
            self.under_minimum = False

    def set_shock(self):
        if random.uniform(0, 1) < self.session.config['shock_rate']:
            self.shock_occurrence = True
            shock_size = random.gauss(self.session.config['shock_size_mean'], self.session.config['shock_size_sd'])
            self.participant.vars['herd_size'] = self.participant.vars['herd_size'] - (shock_size * self.participant.vars['herd_size'])
        else:
            self.shock_occurrence = False
        self.herd_size_after_shock = self.participant.vars['herd_size']
        if self.herd_size_after_shock < c(self.session.config['minherd']):
            self.under_minimum = True
        else:
            self.under_minimum = False

    under_minimum_years_left = models.PositiveIntegerField()

    herd_size_initial = models.CurrencyField()

    herd_size_after_growth = models.CurrencyField()

    shock_occurrence = models.BooleanField()

    herd_size_after_shock = models.CurrencyField()

    under_minimum = models.BooleanField()

    request = models.BooleanField(
        choices=[
            [True, 'Yes'],
            [False, 'No'],
                 ],
        widget=widgets.RadioSelect(),
        verbose_name="Would you like to make a request for cattle?"
    )

    request_player = models.IntegerField()

    request_amount = models.CurrencyField(
        min=c(1),
        verbose_name="How many cattle would you like to request from this player?"
    )

    fulfill1 = models.CurrencyField(verbose_name="How many cattle would you like to give Player 1?")
    fulfill2 = models.CurrencyField(verbose_name="How many cattle would you like to give Player 2?")
    fulfill3 = models.CurrencyField(verbose_name="How many cattle would you like to give Player 3?")
    fulfill4 = models.CurrencyField(verbose_name="How many cattle would you like to give Player 4?")

    def all_transfers(self):
        sender_id = []
        amount_sent = []
        receiver_id = []
        for p in self.group.get_players():
            if p.fulfill1 is not None:
                sender_id.append(p.id_in_group)
                amount_sent.append(p.fulfill1)
                receiver_id.append(1)
            if p.fulfill2 is not None:
                sender_id.append(p.id_in_group)
                amount_sent.append(p.fulfill2)
                receiver_id.append(2)
            if p.fulfill3 is not None:
                sender_id.append(p.id_in_group)
                amount_sent.append(p.fulfill3)
                receiver_id.append(3)
            if p.fulfill4 is not None:
                sender_id.append(p.id_in_group)
                amount_sent.append(p.fulfill4)
                receiver_id.append(4)
        return zip(sender_id, amount_sent, receiver_id)

    def outgoing(self):
        self.participant.vars['herd_size'] -= sum(filter(None, [self.fulfill1, self.fulfill2, self.fulfill3, self.fulfill4]))

    def incoming(self):
        for p in self.group.get_players():
            if self.id_in_group == 1 and p.fulfill1 is not None:
                self.participant.vars['herd_size'] += p.fulfill1
            elif self.id_in_group == 2 and p.fulfill2 is not None:
                self.participant.vars['herd_size'] += p.fulfill2
            elif self.id_in_group == 3 and p.fulfill3 is not None:
                self.participant.vars['herd_size'] += p.fulfill3
            elif self.id_in_group == 4 and p.fulfill4 is not None:
                self.participant.vars['herd_size'] += p.fulfill4

    def final_herd_size(self):
        if self.participant.vars['herd_size'] > c(self.session.config['maxherd']):
            self.participant.vars['herd_size'] = c(self.session.config['maxherd'])
        self.herd_size_after_transfers = c(self.participant.vars['herd_size'])
        if self.herd_size_after_transfers < c(self.session.config['minherd']):
            self.under_minimum = True
            self.participant.vars['under_minimum_years_left'] -= 1
        else:
            self.under_minimum = False
            self.participant.vars['under_minimum_years_left'] = self.session.config['years_before_death']
        self.under_minimum_years_left = self.participant.vars['under_minimum_years_left']
        if self.participant.vars['under_minimum_years_left'] == 0:
            self.participant.vars['dead'] = True

    herd_size_after_transfers = models.CurrencyField()

    def is_playing(self):
        return self.participant.vars['dead'] is False