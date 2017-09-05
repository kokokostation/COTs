from itertools import groupby
from operator import itemgetter
from PyPDF2 import PdfFileReader
import pandas as pd

from validol.model.store.view.view_flavor import ViewFlavor
from validol.model.store.miners.weekly_reports.flavor import Platforms


class DailyView(ViewFlavor):
    def __init__(self, active_cls, actives_cls, flavor):
        self.active_cls = active_cls
        self.actives_cls = actives_cls
        self.flavor = flavor

    def name(self):
        return self.flavor['name']

    def platforms(self, model_launcher):
        return Platforms(model_launcher, self.flavor['name']).get_platforms()

    def actives(self, platform, model_launcher):
        return self.actives_cls(model_launcher, self.flavor['name']).get_actives(platform)

    def active_flavors(self, platform, active, model_launcher):
        return self.active_cls(model_launcher, platform, active, self.flavor).get_flavors()

    def get_df(self, active_info, model_launcher):
        if self.flavor['get_df']:
            return self.active_cls(model_launcher, active_info.platform, active_info.active,
                                   self.flavor).get_flavor(active_info.active_flavor)
        else:
            return pd.DataFrame()

    def get_full_df(self, active_info, model_launcher):
        return self.active_cls(model_launcher, active_info.platform, active_info.active,
                               self.flavor).read_df()

    def remove_active(self, active_info, model_launcher):
        model_launcher.remove_pdf_helper(active_info)

        self.remove_active_data(active_info, model_launcher)

        self.actives_cls(model_launcher, self.flavor['name']).remove_active(active_info)

    def remove_active_data(self, active_info, model_launcher):
        self.active_cls(model_launcher, active_info.platform, active_info.active,
                        self.flavor).drop()

    def get_processors(self):
        return [processor.NAME for processor in self.flavor['processors']]


def active_df_tolist(df):
    return ['{} - {} - {}'.format(item.PlatformCode, item.ActiveCode, item.ActiveName)
            for _, item in df.iterrows()]


def get_pages(fname, phrase):
    pfr = PdfFileReader(fname)
    return [page + 1 for page in range(pfr.getNumPages()) if phrase in pfr.getPage(page).extractText()]


def first_run(items):
    for k, g in groupby(enumerate(items), lambda ix: ix[0] - ix[1]):
        return map(itemgetter(1), g)