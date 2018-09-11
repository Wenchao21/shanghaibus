#    -- coding:utf-8 --

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.listview import ListItemButton
from kivy.properties import ObjectProperty
from kivy.network.urlrequest import UrlRequest
from bs4 import BeautifulSoup
from xpinyin import Pinyin
import json
import urllib.parse
from lxml import etree

bus_list = []
bus_dict = {}
cbusname = ""
query_router_url = 'http://shanghaicity.openservice.kankanews.com/public/bus'
query_bus_sid = "http://shanghaicity.openservice.kankanews.com/public/bus/get"
query_bus_router = "http://shanghaicity.openservice.kankanews.com/public/bus/mes/sid/"
query_bus_stop = "http://shanghaicity.openservice.kankanews.com/public/bus/Getstop"

kivy.resources.resource_add_path(r"C:\Windows\Fonts")
new_font = kivy.resources.resource_find("msyhl.ttc")     # Android DroidSansFallback.ttf   Windows:


def render_listbutton(listobject, data):
    listobject.adapter.data.clear()
    listobject.adapter.cls.font_name = new_font
    listobject.adapter.data.extend(data)
    listobject._trigger_reset_populate()


class UpdateBusList():
    def __init__(self):
        self.get_bus_list()

    def get_bus_list(self):
        req = UrlRequest(query_router_url, on_success=self.parse_bus_list)
        req.wait()

    def parse_bus_list(self, req, result):
        global bus_list, bus_dict
        soup = BeautifulSoup(result, "html.parser")
        for line in soup.find_all("script")[2]:
            if "var data = " in line:
                bus_list = [str(eval(x)) for x in line.split("[")[1].split("];")[0].split(",")]
            else:
                bus_list = []
        p = Pinyin()
        bus_dict = {p.get_initials(x, ""): x for x in bus_list}
        print(bus_dict)
        with open("buslist.txt", "w", encoding="utf-8") as f:
            f.write(str(bus_dict))
        print(bus_list)


class RootWidget(BoxLayout):
    query_form = ObjectProperty()

    def __init__(self, **kwargs):
        super(RootWidget, self).__init__(**kwargs)
        self.query_form.search_label.text = "公交名称"
        self.query_form.search_label.font_name = new_font

    def add_widgets(self, widgets):
        self.add_widget(widgets)


class QueryStation(BoxLayout):
    bus_names = ObjectProperty()
    search_input = ObjectProperty()
    search_label = ObjectProperty()

    def input_filter(self):
        filter_bus_list = []
        input = self.search_input.text.upper()
        for name in bus_dict.keys():
            if name.startswith(input):
                filter_bus_list.append(bus_dict[name])
        render_listbutton(self.bus_names, filter_bus_list)


class BusRouter(BoxLayout):
    bus_name_label = ObjectProperty()
    bus_direction_listbutton = ObjectProperty()
    bus_station_listbutton = ObjectProperty()
    bus_station_label = ObjectProperty()
    return_button = ObjectProperty()
    bus_direction = 0

    def __init__(self, font_name, busname, ftolinfo_data, bus_stations, bus_stations_reverse, sid, **kwargs):
        super(BusRouter, self).__init__(**kwargs)
        self.bus_name_label.font_name = font_name
        self.bus_name_label.text = busname
        self.bus_station_label.font_name = font_name
        self.bus_station_label.text = "公交站点信息"
        self.return_button.font_name = font_name
        self.return_button.text = "返回"
        self.busname = busname
        self.ftolinfo = ftolinfo_data
        self.bus_stations = bus_stations
        self.bus_stations_reverse = bus_stations_reverse
        self.sid = sid
        render_listbutton(self.bus_direction_listbutton, self.ftolinfo)
        render_listbutton(self.bus_station_listbutton, self.bus_stations)

    def return_pre(self):
        rootwidget = self.get_parent_window().children[0]
        rootwidget.clear_widgets()
        rootwidget.add_widget(QueryStation())


class BusDirection(ListItemButton):
    def change_bus_direction(self):
        rootwidget = self.get_parent_window().children[0]
        busrouter_widget = rootwidget.children[0]
        if self.index == 1:
            render_listbutton(busrouter_widget.bus_station_listbutton, busrouter_widget.bus_stations_reverse)
            busrouter_widget.bus_direction = 1
        elif self.index == 0:
            render_listbutton(busrouter_widget.bus_station_listbutton, busrouter_widget.bus_stations)
            busrouter_widget.bus_direction = 0


class BusStation(ListItemButton):
    def show_station(self):
        rootwidget = self.get_parent_window().children[0]
        busrouter_widget = rootwidget.children[0]
        direction = busrouter_widget.bus_direction
        sid = busrouter_widget.sid
        stopid = self.text.split(".")[0]
        data = {"stoptype": direction, "stopid": stopid, "sid": sid}
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Accept': 'text/plain'}
        req = UrlRequest(query_bus_stop, req_headers=headers, req_body=urllib.parse.urlencode(data),
                         on_success=self.parse_stop_info)
        req.wait()
        rootwidget.clear_widgets()
        rootwidget.add_widget(Label(text=self.bus+self.bus_code+self.bus_distance+str(self.bus_time),
                                    font_name=new_font))

    def parse_stop_info(self, req, result):
        print(result)
        self.bus = json.loads(result)[0]["@attributes"]["cod"]
        self.bus_code = json.loads(result)[0]["terminal"]
        self.bus_distance = json.loads(result)[0]["stopdis"]
        self.bus_time = int(json.loads(result)[0]["time"])//60
        print(self.bus, self.bus_code, self.bus_distance, self.bus_time)


class BusListButton(ListItemButton):

    def __init__(self, **kwargs):
        super(BusListButton, self).__init__(**kwargs)
        self.sid = ""
        self.ftolinfo = []
        self.bus_stations = []
        self.bus_stations_reverse = []

    def show_bus_router(self):
        global cbusname
        cbusname = self.text
        rootwidget = self.get_parent_window().children[0]              # get_parent_windows return list
#        print(dir(self.get_parent_window()))                          get the original  windows, not to init again
        print(self.get_parent_window().children)
        self.get_bus_router()
        rootwidget.clear_widgets()
        rootwidget.add_widget(BusRouter(new_font, cbusname, self.ftolinfo, self.bus_stations,
                                        self.bus_stations_reverse, self.sid))
        print(new_font, cbusname, self.ftolinfo, self.bus_stations, self.sid)

    def get_bus_router(self):
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Accept': 'text/plain'}
        params = urllib.parse.urlencode({"idnum": cbusname})
        req = UrlRequest(query_bus_sid, on_success=self.parse_bus_id, req_body=params, on_error=self.print_error,
                         method="POST", req_headers=headers)
        req.wait()

    def print_error(self, req, error):
        print(req, error)

    def parse_bus_id(self, req, result):
        self.sid = json.loads(result)["sid"]
        for i in [0, 1]:
            url = "{0}/{1}/stoptype/{2}".format(query_bus_router, self.sid, i)
            if i == 0:
                request = UrlRequest(url, on_success=self.parse_bus_router, on_error=self.print_error,
                                     on_failure=self.print_failure)
                request.wait()
            else:
                request = UrlRequest(url, on_success=self.parse_bus_router_reverse)
                request.wait()

    def print_failure(self, req, result):
        print(req, result)

    def parse_bus_router(self, req, result):
        selector = etree.HTML(result)
        ftolstation = selector.xpath("//div[@class='upgoing cur' or @class='downgoing ']/p/span/text()")
        ftoltime = selector.xpath("//div[@class='upgoing cur' or @class='downgoing ']/div/em/text()")
        print("ftol", ftolstation, ftoltime)
        for i in [0, 2]:
            self.ftolinfo.append("{0}-->{1}    首班车:{2}  末班车{3}".format(ftolstation[i], ftolstation[i+1],
                                                                       ftoltime[i], ftoltime[i+1]))
        bus_stations_temp = selector.xpath("//span[@class='name']/text()")
        self.bus_stations = ["{0}.{1}".format(i+1, bus_stations_temp[i])for i in range(len(bus_stations_temp))]
        print(self.bus_stations)

    def parse_bus_router_reverse(self, req, result):
        selector = etree.HTML(result)
        bus_stations_reverse_temp = selector.xpath("//span[@class='name']/text()")
        self.bus_stations_reverse = \
            ["{0}.{1}".format(i+1, bus_stations_reverse_temp[i]) for i in range(len(bus_stations_reverse_temp))]









class ShanghaiBusApp(App):
    bus_update = UpdateBusList()


if __name__ == "__main__":
    ShanghaiBusApp().run()