from otree.api import Currency as c, currency_range, Submission
from . import views
from ._builtin import Bot
from .models import Constants
import random


class PlayerBot(Bot):
    def play_round(self):
        if self.player.is_playing():
            yield (views.NewYear)
            yield (views.Growth)
            yield (views.Shock)
            yield (views.Request, {'request': True})
            if self.player.id_in_group == 1:
                request_player = 2
            elif self.player.id_in_group == 2:
                request_player = 3
            else:
                request_player = 1
            yield (views.RequestPlayer, {'request_player': request_player})
            yield (views.RequestAmount, {'request_amount': 5})
            amount_sent = random.randint(0, self.participant.vars['herd_size'])
            recipient = [p.id for p in self.player.sender.all()][0]
            fulfill_dict = {
                'sender-INITIAL_FORMS': (1, 1),
                'sender-TOTAL_FORMS': (1, 1),
                'sender-0-sender': self.player.pk,
                'sender-0-id': recipient,
                'sender-0-amount_sent': amount_sent,
            }
            yield (views.Fulfill, fulfill_dict)
            yield (views.AllTransfers)
            yield (views.EndYear)
        if self.player.dead:
            yield (views.Dead)
        if self.round_number == Constants.num_rounds:
            yield Submission(views.EndExperiment, check_html=False)
