from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants, Player
import django
from django import forms


class NewYear(Page):
    def is_displayed(self):
        return self.player.is_playing()

    def vars_for_template(self):
        return {'round_number': self.subsession.round_number}

    def before_next_page(self):
        self.player.set_growth()
        self.player.set_under_minimum_years_left()


class Growth(Page):
    def is_displayed(self):
        return self.player.is_playing()

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'minherd': self.session.config['minherd'],
                'round_number': self.subsession.round_number,
                'herd_size_initial': self.player.herd_size_initial,
                'herd_size_after_growth': self.player.herd_size_after_growth,
                'other_players': self.player.get_others_in_group()}

    def before_next_page(self):
        self.player.set_shock()


class Shock(Page):
    def is_displayed(self):
        return self.player.is_playing()

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'minherd': self.session.config['minherd'],
                'round_number': self.subsession.round_number,
                'herd_size_after_growth': self.player.herd_size_after_growth,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'shock_occurrence': self.player.shock_occurrence,
                'other_players': self.player.get_others_in_group()}


class Request(Page):
    form_model = models.Player
    form_fields = ['request']

    def is_displayed(self):
        return self.player.is_playing()

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'minherd': self.session.config['minherd'],
                'round_number': self.subsession.round_number,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'other_players': self.player.get_others_in_group()
                }

    def before_next_page(self):
        self.group.no_requests()


class RequestPlayerForm(forms.Form):
    def __init__(self, choices, *args, **kwargs):
        super(RequestPlayerForm, self).__init__(*args, **kwargs)
        self.fields['request_player'] = django.forms.CharField(
            widget=django.forms.RadioSelect(choices=choices),
            label='Which player would you like to request cattle from?')


class RequestPlayer(Page):
    def is_displayed(self):
        return self.player.is_playing() and self.player.request

    form_model = models.Player
    form_fields = ['request_player']

    def vars_for_template(self):
        others = self.player.get_others_in_group()
        # we need to show to Player 1 the choice of Player 2 and Player 3, and so on
        choices = [(p.id_in_group, "Player {}".format(p.id_in_group)) for p in others]
        requestplayerform = RequestPlayerForm(tuple(choices))
        return {'myform': requestplayerform,
                'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'minherd': self.session.config['minherd'],
                'round_number': self.subsession.round_number,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'other_players': self.player.get_others_in_group()
                }


class RequestAmount(Page):
    form_model = models.Player
    form_fields = ['request_amount']

    def request_amount_max(self):
        return self.session.config['maxherd'] - self.participant.vars['herd_size']

    def is_displayed(self):
        return self.player.is_playing() and self.player.request

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'minherd': self.session.config['minherd'],
                'round_number': self.subsession.round_number,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'other_players': self.player.get_others_in_group(),
                'request_player': self.player.request_player,
                }


class Fulfill(Page):
    form_model = models.Player

    def get_form_fields(self):
        request_me = []
        others = self.player.get_others_in_group()
        for o in others:
            if o.request_player == self.player.id_in_group:
                request_me.append(o.id_in_group)
        return ['fulfill{}'.format(p) for p in request_me]

    def fulfill1_max(self):
        return self.participant.vars['herd_size']

    def fulfill2_max(self):
        return self.participant.vars['herd_size']

    def fulfill3_max(self):
        return self.participant.vars['herd_size']

    def fulfill4_max(self):
        return self.participant.vars['herd_size']

    def error_message(self, values):
        n = []
        for p in self.group.get_players():
            if p.request_player == self.player.id_in_group:
                n.append(p.id_in_group)
        if n == [1, 2]:
            if values["fulfill1"] + values["fulfill2"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [1, 3]:
            if values["fulfill1"] + values["fulfill3"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [1, 4]:
            if values["fulfill1"] + values["fulfill4"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [2, 3]:
            if values["fulfill2"] + values["fulfill3"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [2, 4]:
            if values["fulfill2"] + values["fulfill4"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [3, 4]:
            if values["fulfill3"] + values["fulfill4"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [1, 2, 3]:
            if values["fulfill1"] + values["fulfill2"] + values["fulfill3"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [1, 2, 4]:
            if values["fulfill1"] + values["fulfill2"] + values["fulfill4"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [1, 3, 4]:
            if values["fulfill1"] + values["fulfill3"] + values["fulfill4"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'
        if n == [2, 3, 4]:
            if values["fulfill2"] + values["fulfill3"] + values["fulfill4"] > self.participant.vars['herd_size']:
                return 'In total, you have attempted to transfer more cattle than you currently own. Please try again.'

    def vars_for_template(self):
        request_me = 0
        others = self.player.get_others_in_group()
        for o in others:
            if o.request_player == self.player.id_in_group:
                request_me += 1
        return {'request_me': request_me, 'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'minherd': self.session.config['minherd'],
                'round_number': self.subsession.round_number,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'other_players': self.player.get_others_in_group(),
                'request_player': self.player.request_player,
                }

    def is_displayed(self):
        return self.player.is_playing() and self.group.norequests is False


class AllTransfers(Page):
    def vars_for_template(self):
        all_transfers = self.player.all_transfers()
        return {'norequests': self.group.norequests,
                'all_transfers': all_transfers,
                'round_number': self.subsession.round_number}

    def is_displayed(self):
        return self.player.is_playing()

    def before_next_page(self):
        self.player.incoming()
        self.player.outgoing()
        self.player.final_herd_size()


class EndYear(Page):
    def is_displayed(self):
        return self.player.is_playing()

    def vars_for_template(self):
        return {'round_number': self.subsession.round_number,
                'herd_size_after_transfers': self.player.herd_size_after_transfers,
                'other_players': self.player.get_others_in_group(),
                'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'under_minimum_years_before_death': self.session.config['years_before_death'],
                'minherd': self.session.config['minherd'],
                'dead': self.participant.vars['dead']
                }


class Dead(Page):
    def is_displayed(self):
        return self.subsession.round_number == Constants.num_rounds


page_sequence = [
    NewYear,
    WaitPage,
    Growth,
    WaitPage,
    Shock,
    Request,
    WaitPage,
    RequestPlayer,
    RequestAmount,
    WaitPage,
    Fulfill,
    WaitPage,
    AllTransfers,
    WaitPage,
    EndYear
]
