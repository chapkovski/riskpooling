from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants, Player, SendReceive
import django
from django import forms
from .forms import SRFormSet
from django.db.models import Q


def vars_for_all_templates(self):
    return {'herd_size_for_chart': int(self.player.participant.vars['herd_size']),
            'observability': self.session.config['observability'],
            'round_number': self.subsession.round_number,
            'minherd': self.session.config['minherd'],
            'charts': self.session.config['charts']
            }


class Wait(WaitPage):
    def is_displayed(self):
        return self.player.is_playing()


class NewYear(Page):
    def is_displayed(self):
        return self.player.is_playing()

    def before_next_page(self):
        self.player.set_growth()
        self.player.set_under_minimum_years_left()


class NumPlayingWait(WaitPage):
    def is_displayed(self):
        return self.player.is_playing()

    def after_all_players_arrive(self):
        self.group.set_num_playing()


class Growth(Page):
    def is_displayed(self):
        return self.player.is_playing()

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'herd_size_initial': self.player.herd_size_initial,
                'herd_size_after_growth': self.player.herd_size_after_growth,
                'other_players': self.player.get_others_in_group(),
                'num_players': self.group.num_playing,
                'dead_remove': self.player.dead_remove
                }

    def before_next_page(self):
        self.player.set_shock()


class Shock(Page):
    def is_displayed(self):
        return self.player.is_playing()

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'herd_size_after_growth': self.player.herd_size_after_growth,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'shock_occurrence': self.player.shock_occurrence,
                'other_players': self.player.get_others_in_group(),
                'num_players': self.group.num_playing,
                'dead_remove': self.player.dead_remove
                }


class NoPlayersToRequest(Page):
    def is_displayed(self):
        return self.player.is_playing() and self.group.num_playing == 1

    def vars_for_template(self):
        return {'herd_size_after_shock': self.player.herd_size_after_shock}


class Request(Page):
    form_model = models.Player
    form_fields = ['request']

    def is_displayed(self):
        return self.player.is_playing() and self.group.num_playing > 1

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'other_players': self.player.get_others_in_group(),
                'num_players': self.group.num_playing,
                'dead_remove': self.player.dead_remove
                }

    def before_next_page(self):
        self.player.set_request_player()


class RequestsWait(WaitPage):
    def is_displayed(self):
        return self.player.is_playing() and self.group.num_playing > 1

    def after_all_players_arrive(self):
        self.group.no_requests()


class RequestPlayer(Page):
    def is_displayed(self):
        return self.player.is_playing() and self.player.request and self.group.num_playing > 2

    form_model = models.Player
    form_fields = ['request_player']

    def request_player_choices(self):
        choices = []
        for o in self.player.get_others_in_group():
            choices.append((o.id_in_group, "Player {}".format(o.id_in_group)))
        return choices

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'other_players': self.player.get_others_in_group(),
                'dead_remove': self.player.dead_remove,
                }


class RequestAmount(Page):
    form_model = models.Player
    form_fields = ['request_amount']

    def request_amount_max(self):
        return self.session.config['maxherd'] - self.participant.vars['herd_size']

    def is_displayed(self):
        return self.player.is_playing() and self.player.request and self.group.num_playing > 1

    def vars_for_template(self):
        return {'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'other_players': self.player.get_others_in_group(),
                'request': self.player.request,
                'request_player': self.player.request_player,
                'num_players': self.group.num_playing,
                'dead_remove': self.player.dead_remove,
                }

    def before_next_page(self):
        if self.player.request:
            target = Player.objects.get(id_in_group=self.player.request_player, subsession=self.subsession, group=self.group)
            sr, created = self.player.receiver.get_or_create(sender=target,
                                                             defaults={'amount_requested': self.player.request_amount})
            sr.save()


class Fulfill(Page):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formset'] = SRFormSet(instance=self.player)
        return context

    def post(self):
        context = super().get_context_data()
        formset = SRFormSet(self.request.POST, instance=self.player)
        context['formset'] = formset
        if not formset.is_valid():
            return self.render_to_response(context)
        formset.save()
        return super().post()

    def before_next_page(self):
        to_dump_sender = self.player.sender.values('receiver__id_in_group', 'amount_sent', 'amount_requested', )
        to_dump_receiver = self.player.receiver.values('sender__id_in_group', 'amount_sent', 'amount_requested', )
        self.player.sr_dump = {'sending': to_dump_sender,
                               'receiving': to_dump_receiver}

    def vars_for_template(self):
        request_me = 0
        others = self.player.get_others_in_group()
        for o in others:
            if o.request_player == self.player.id_in_group:
                request_me += 1
        return {'request_me': request_me,
                'under_minimum': self.player.under_minimum,
                'under_minimum_years_left': self.player.under_minimum_years_left,
                'herd_size_after_shock': self.player.herd_size_after_shock,
                'other_players': self.player.get_others_in_group(),
                'request': self.player.request,
                'request_player': self.player.request_player,
                'request_amount': self.player.request_amount,
                'num_players': self.group.num_playing,
                'dead_remove': self.player.dead_remove,
                }

    def is_displayed(self):
        request_me = 0
        others = self.player.get_others_in_group()
        for o in others:
            if o.request_player == self.player.id_in_group and o.request is True:
                request_me += 1
        return self.player.is_playing() and self.group.norequests is False \
               and self.group.num_playing > 1 and request_me > 0


class NoTransfers(Page):
    def is_displayed(self):
        return self.player.is_playing() and self.group.num_playing > 1 and self.group.norequests

    def vars_for_template(self):
        return {'herd_size_after_shock': self.player.herd_size_after_shock,
                }


class TransferWait(WaitPage):
    def is_displayed(self):
        return self.player.is_playing()

    def after_all_players_arrive(self):
        self.group.incoming()
        self.group.outgoing()
        self.group.final_herd_size()


class AllTransfers(Page):
    def vars_for_template(self):
        aps = self.group.get_players()
        all_transfers = \
            SendReceive.objects.filter(Q(sender__in=aps) | Q(receiver__in=aps)).values('sender__id_in_group',
                                                                                       'receiver__id_in_group',
                                                                                       'amount_sent')
        print(all_transfers)
        return {'all_transfers': all_transfers,
                'herd_size_after_transfers': self.player.herd_size_after_transfers,
                'request': self.player.request,
                'request_player': self.player.request_player,
                'request_amount': self.player.request_amount,
                }

    def is_displayed(self):
        return self.player.is_playing() and self.group.num_playing > 1 and not self.group.norequests


class EndYear(Page):
    def is_displayed(self):
        return self.player.is_playing()

    def vars_for_template(self):
        aps = self.group.get_players()
        all_transfers = SendReceive.objects.filter(Q(sender__in=aps) | Q(receiver__in=aps)).values(
            'sender__id_in_group',
            'receiver__id_in_group',
            'amount_sent')
        print(all_transfers)
        return {'all_transfers': all_transfers,
                'herd_size_after_transfers': self.player.herd_size_after_transfers,
                'other_players': self.player.get_others_in_group(),
                'under_minimum': self.player.under_minimum,
                'under_minimum_years_left_end': self.player.under_minimum_years_left_end,
                'under_minimum_years_before_death': self.session.config['years_before_death'],
                'dead': self.player.dead,
                'num_players': self.group.num_playing,
                'dead_remove': self.player.dead_remove,
                'request': self.player.request,
                'request_player': self.player.request_player,
                'request_amount': self.player.request_amount,
                }

    def before_next_page(self):
        self.player.set_dead()
        if self.player.dead:
            self.player.set_remove_from_game()
        elif self.player.dead is not True and self.round_number == Constants.num_rounds:
            self.player.in_round(Constants.num_rounds).rounds_survived = Constants.num_rounds
            self.player.set_payoff_and_dvs()


class Dead(Page):
    def is_displayed(self):
        return self.player.dead


class EndExperiment(Page):
    def is_displayed(self):
        return self.subsession.round_number == Constants.num_rounds


page_sequence = [
    NewYear,
    NumPlayingWait,
    Growth,
    Wait,
    Shock,
    NoPlayersToRequest,
    Wait,
    Request,
    RequestsWait,
    RequestPlayer,
    RequestAmount,
    Wait,
    Fulfill,
    Wait,
    NoTransfers,
    TransferWait,
    AllTransfers,
    EndYear,
    Dead,
    Wait,
    EndExperiment
]
