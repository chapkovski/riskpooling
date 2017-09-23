from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
import random
from django.db import models as djmodels
from django.db.models import Q, Sum

author = 'Scott Claessens'

doc = """Risk-pooling game"""


class Constants(BaseConstants):
    name_in_url = 'riskpooling'
    players_per_group = 3
    num_rounds = 20


class Subsession(BaseSubsession):
    def vars_for_admin_report(self):
        aps = self.get_players()
        all_transfers = SendReceive.objects.filter(Q(sender__in=aps) | Q(receiver__in=aps)).values(
            'sender__id_in_group',
            'receiver__id_in_group',
            'amount_sent',
            'amount_requested',
            'sender__group__id_in_subsession')

        return {'all_transfers': all_transfers}

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

    def set_num_playing(self):
        n = 0
        for p in self.get_players():
            if p.dead_remove:
                n += 1
        self.num_playing = Constants.players_per_group - n

    def outgoing(self):
        if self.norequests is False:
            for p in self.get_players():
                tot_sent = (p.sender.aggregate(tot_sent=Sum('amount_sent'))['tot_sent'] or 0)
                p.participant.vars['herd_size'] -= tot_sent

    def incoming(self):
        if self.norequests is False:
            for p in self.get_players():
                tot_received = (p.receiver.aggregate(tot_received=Sum('amount_sent'))['tot_received'] or 0)
                p.participant.vars['herd_size'] += tot_received
                if p.request:
                    p.received = tot_received

    def final_herd_size(self):
        for n in self.get_players():
            if n.participant.vars['herd_size'] > c(self.session.config['maxherd']):
                n.participant.vars['herd_size'] = c(self.session.config['maxherd'])
            if n.participant.vars['herd_size'] <= c(0):
                n.participant.vars['herd_size'] = c(0)
            if n.dead_remove is not True:
                n.herd_size_after_transfers = c(n.participant.vars['herd_size'])
                if n.herd_size_after_transfers < c(self.session.config['minherd']):
                    n.under_minimum = True
                    n.participant.vars['under_minimum_years_left'] -= 1
                else:
                    n.under_minimum = False
                    n.participant.vars['under_minimum_years_left'] = self.session.config['years_before_death']
                n.under_minimum_years_left_end = n.participant.vars['under_minimum_years_left']
                if n.under_minimum_years_left_end == 0:
                    n.dead = True
                else:
                    n.dead = False

    norequests = models.BooleanField()

    num_playing = models.PositiveIntegerField()


class Player(BasePlayer):
    def set_under_minimum_years_left(self):
        self.under_minimum_years_left = self.participant.vars['under_minimum_years_left']

    def set_growth(self):
        if self.dead_remove is not True:
            self.herd_size_initial = self.participant.vars['herd_size']
            growth_rate = random.gauss(self.session.config['growth_rate_mean'], self.session.config['growth_rate_sd'])
            self.participant.vars['herd_size'] = \
                self.participant.vars['herd_size'] + (growth_rate * self.participant.vars['herd_size'])
            if self.participant.vars['herd_size'] > c(self.session.config['maxherd']):
                self.participant.vars['herd_size'] = c(self.session.config['maxherd'])
            if self.participant.vars['herd_size'] <= c(0):
                self.participant.vars['herd_size'] = c(0)
            self.herd_size_after_growth = self.participant.vars['herd_size']
            if self.herd_size_after_growth < c(self.session.config['minherd']):
                self.under_minimum = True
            else:
                self.under_minimum = False

    def set_shock(self):
        if self.dead_remove is not True:
            if random.uniform(0, 1) < self.session.config['shock_rate']:
                self.shock_occurrence = True
                shock_size = random.gauss(self.session.config['shock_size_mean'], self.session.config['shock_size_sd'])
                self.participant.vars['herd_size'] = \
                    self.participant.vars['herd_size'] - (shock_size * self.participant.vars['herd_size'])
            else:
                self.shock_occurrence = False
            if self.participant.vars['herd_size'] > c(self.session.config['maxherd']):
                self.participant.vars['herd_size'] = c(self.session.config['maxherd'])
            if self.participant.vars['herd_size'] <= c(0):
                self.participant.vars['herd_size'] = c(0)
            self.herd_size_after_shock = self.participant.vars['herd_size']
            if self.herd_size_after_shock < c(self.session.config['minherd']):
                self.under_minimum = True
            else:
                self.under_minimum = False

    def set_request_player(self):
        if self.group.num_playing == 2:
            for o in self.get_others_in_group():
                if o.dead_remove is not True:
                    self.request_player = o.id_in_group

    def set_dead(self):
        if self.dead:
            self.participant.vars['dead'] = True

    def set_remove_from_game(self):
        for n in range(1, Constants.num_rounds+1):
            if self.in_round(n).dead is None:
                self.in_round(n).dead_remove = True
        self.in_round(Constants.num_rounds).rounds_survived = self.round_number
        self.set_payoff_and_dvs()

    def set_payoff_and_dvs(self):
        self.participant.payoff = sum(
            [p.herd_size_after_transfers for p in self.in_all_rounds()]) / Constants.num_rounds
        n = 0
        for r in range(1, Constants.num_rounds+1):
            if self.in_round(r).dead_remove is not True:
                n += 1
        self.in_round(Constants.num_rounds).overall_total_amount_requested = sum(filter(None,
            [p.request_amount for p in self.in_all_rounds()]))
        self.in_round(Constants.num_rounds).overall_total_amount_given = sum(filter(None,
            [(p.sender.aggregate(tot_sent=Sum('amount_sent'))['tot_sent'] or 0) for p in self.in_all_rounds()]))
        self.in_round(Constants.num_rounds).overall_requested_given_diff = \
            self.in_round(Constants.num_rounds).overall_total_amount_requested - \
            self.in_round(Constants.num_rounds).overall_total_amount_given
        self.in_round(Constants.num_rounds).overall_mean_amount_requested = sum(filter(None,
            [p.request_amount for p in self.in_all_rounds()])) / n
        self.in_round(Constants.num_rounds).overall_mean_amount_given = sum(filter(None,
            [(p.sender.aggregate(tot_sent=Sum('amount_sent'))['tot_sent'] or 0) for p in self.in_all_rounds()])
        ) / n
        a = 0
        for r in range(1, Constants.num_rounds+1):
            if self.in_round(r).request:
                a += 1
        self.in_round(Constants.num_rounds).overall_num_requests_made = a
        # still need:
        #
        # overall_num_requests_responded_to
        # overall_repetitive_giving
        # overall_repetitive_asking

    def is_playing(self):
        return self.participant.vars['dead'] is False

    under_minimum_years_left = models.PositiveIntegerField()

    herd_size_initial = models.CurrencyField()

    herd_size_after_growth = models.CurrencyField()

    shock_occurrence = models.BooleanField()

    herd_size_after_shock = models.CurrencyField()

    request = models.BooleanField(
        choices=[
            [True, 'Yes'],
            [False, 'No'],
                 ],
        widget=widgets.RadioSelect(),
        verbose_name="Would you like to make a request for cattle?"
    )

    request_player = models.IntegerField(
        widget=widgets.RadioSelect(),
        verbose_name="Which player would you like to request cattle from?"
    )

    request_amount = models.CurrencyField(
        min=c(1),
        verbose_name="How many cattle would you like to request from this player?"
    )

    sr_dump = models.CharField()

    received = models.CurrencyField()

    herd_size_after_transfers = models.CurrencyField()

    under_minimum_years_left_end = models.PositiveIntegerField()

    under_minimum = models.BooleanField()

    dead = models.BooleanField()

    dead_remove = models.BooleanField()

    rounds_survived = models.IntegerField()

    overall_total_amount_requested = models.CurrencyField()

    overall_total_amount_given = models.CurrencyField()

    overall_requested_given_diff = models.CurrencyField()

    overall_mean_amount_requested = models.CurrencyField()

    overall_mean_amount_given = models.CurrencyField()

    overall_num_requests_made = models.IntegerField()

    overall_num_requests_responded_to = models.IntegerField()

    overall_repetitive_giving = models.IntegerField()

    overall_repetitive_asking = models.IntegerField()


class SendReceive(djmodels.Model):
    receiver = djmodels.ForeignKey(Player, related_name='receiver')
    sender = djmodels.ForeignKey(Player, related_name='sender')
    amount_requested = models.IntegerField()
    amount_sent = models.IntegerField(blank=True)
