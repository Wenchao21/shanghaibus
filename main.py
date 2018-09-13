#    -- coding:utf-8 --

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.listview import ListItemButton
from kivy.uix.image import Image
from kivy.properties import ObjectProperty
from kivy.network.urlrequest import UrlRequest
from bs4 import BeautifulSoup
from xpinyin import Pinyin
import json
import urllib.parse
from lxml import etree


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


def get_root_widget(par):                                        # get the original  windows, not to init again
    return par.get_parent_window().children[0]                   # get_parent_windows return list


class UpdateBusList():
    def __init__(self):
        self.get_bus_list()

    def get_bus_list(self):
        req = UrlRequest(query_router_url, on_success=self.parse_bus_list)
        req.wait()

    def parse_bus_list(self, req, result):
        soup = BeautifulSoup(result, "html.parser")
        for line in soup.find_all("script")[2]:
            if "var data = " in line:
                bus_list = [str(eval(x)) for x in line.split("[")[1].split("];")[0].split(",")]
            else:
                bus_list = []
        p = Pinyin()
        bus_dict = {p.get_initials(x, ""): x for x in bus_list}
        with open("buseslist.txt", "w", encoding="utf-8") as f:
            f.write(str(bus_dict))


class RootWidget(BoxLayout):                                  # 程序执行后生成一个主窗口的实例，控件的所有操作必须在此实例内
    query_form = ObjectProperty()                             # 程序内调用RootWidget会生成新的实例

    def __init__(self, **kwargs):
        super(RootWidget, self).__init__(**kwargs)
        self.query_form.search_label.text = "公交名称"
        self.query_form.search_label.font_name = new_font


class QueryBus(BoxLayout):
    search_input = ObjectProperty()
    search_label = ObjectProperty()
    bus_names = ObjectProperty()

    def __init__(self, **kwargs):
        super(QueryBus, self).__init__(**kwargs)
        with open("buseslist.txt", "r", encoding="utf-8") as f:
            self.bus_dict = eval(f.readline())

    def input_filter(self):
        filter_bus_list = []
        bus_input = self.search_input.text.upper()
        for name in self.bus_dict.keys():
            if name.startswith(bus_input):
                filter_bus_list.append(self.bus_dict[name])
        render_listbutton(self.bus_names, filter_bus_list)


class ColorLabel(Label):
    pass


class BusesListButton(ListItemButton):

    def __init__(self, **kwargs):
        super(BusesListButton, self).__init__(**kwargs)
        self.sid = ""
        self.ftolinfo = []
        self.bus_stations = []
        self.bus_stations_reverse = []
        self.cbusname = ""

    def show_bus_router(self):
        self.cbusname = self.text
        self.rootwidget = get_root_widget(self)      # 在主窗口确定被渲染的情况下，把其存放在实例变量中，供特定使用
        self.get_bus_router()
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(Image(source="ezgif-2-8219edf39b-gif-png.zip"))

    def get_bus_router(self):
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Accept': 'text/plain'}
        params = urllib.parse.urlencode({"idnum": self.cbusname})
        req = UrlRequest(query_bus_sid, on_success=self.parse_bus_id, req_body=params, on_error=self.print_error,
                         method="POST", req_headers=headers, on_failure=self.print_failure)

    def print_error(self, req, error):                    # 回调函数中无法直接使用get_parent_window(), get_root_window()
        if error.strerror == 'getaddrinfo failed':        # 回调函数延时执行，可能主窗口没有被渲染， 返回值为None
            self.rootwidget.clear_widgets()
            self.rootwidget.add_widget(Label(text="请检查你的网络", font_name=new_font))

    def parse_bus_id(self, req, result):
        self.sid = json.loads(result)["sid"]
        for i in [0, 1]:
            url = "{0}/{1}/stoptype/{2}".format(query_bus_router, self.sid, i)
            if i == 0:
                request = UrlRequest(url, on_success=self.parse_bus_router, on_error=self.print_error,
                                     on_failure=self.print_failure)
            else:
                request = UrlRequest(url, on_success=self.parse_bus_router_reverse)

    def print_failure(self, req, result):
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(Label(text=str(result), font_name=new_font))

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
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(BusRouter(self.cbusname, self.ftolinfo, self.bus_stations,
                                             self.bus_stations_reverse, self.sid))

    def parse_bus_router_reverse(self, req, result):
        selector = etree.HTML(result)
        bus_stations_reverse_temp = selector.xpath("//span[@class='name']/text()")
        self.bus_stations_reverse = \
            ["{0}.{1}".format(i+1, bus_stations_reverse_temp[i]) for i in range(len(bus_stations_reverse_temp))]
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(BusRouter(self.cbusname, self.ftolinfo, self.bus_stations,
                                             self.bus_stations_reverse, self.sid))


class BusRouter(BoxLayout):
    bus_name_label = ObjectProperty()
    bus_direction_listbutton = ObjectProperty()
    bus_station_listbutton = ObjectProperty()
    bus_station_label = ObjectProperty()
    return_button = ObjectProperty()
    bus_direction = 0
    bus_direction_name = ""

    def __init__(self, busname, ftolinfo_data, bus_stations, bus_stations_reverse, sid, **kwargs):
        super(BusRouter, self).__init__(**kwargs)
        self.bus_name_label.font_name = new_font
        self.bus_name_label.text = busname
        self.bus_station_label.font_name = new_font
        self.bus_station_label.text = "公交站点信息"
        self.return_button.font_name = new_font
        self.return_button.text = "返回"
        self.ftolinfo = ftolinfo_data
        self.bus_stations = bus_stations
        self.bus_stations_reverse = bus_stations_reverse
        self.sid = sid
        render_listbutton(self.bus_direction_listbutton, self.ftolinfo)
        render_listbutton(self.bus_station_listbutton, self.bus_stations)

    def return_pre(self):
        rootwidget = self.get_parent_window().children[0]
        rootwidget.clear_widgets()
        rootwidget.add_widget(QueryBus())


class BusDirection(ListItemButton):
    def __init__(self, **kwargs):
        super(BusDirection, self).__init__(**kwargs)
 #       self.get_parent_window().children[0].children[0].bus_direction_name = self.text

    def change_bus_direction(self):
        rootwidget = self.get_parent_window().children[0]
        busrouter_widget = rootwidget.children[0]
        busrouter_widget.bus_direction_name = self.text
        if self.index == 1:
            render_listbutton(busrouter_widget.bus_station_listbutton, busrouter_widget.bus_stations_reverse)
            busrouter_widget.bus_direction = 1
        elif self.index == 0:
            render_listbutton(busrouter_widget.bus_station_listbutton, busrouter_widget.bus_stations)
            busrouter_widget.bus_direction = 0


class BusStation(ListItemButton):
    def query_stop_info(self):
        self.rootwidget = self.get_parent_window().children[0]
        self.busrouter_widget = self.rootwidget.children[0]
        direction = self.busrouter_widget.bus_direction
        sid = self.busrouter_widget.sid
        stopid = self.text.split(".")[0]
        self.data = {"stoptype": direction, "stopid": stopid, "sid": sid}
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Accept': 'text/plain'}
        req = UrlRequest(query_bus_stop, req_headers=headers, req_body=urllib.parse.urlencode(self.data),
                         on_success=self.parse_stop_info)
        self.rootwidget.clear_widgets()
        self.rootwidget.remove_widget(Image(source="ezgif-2-8219edf39b-gif-png.zip"))

    def parse_stop_info(self, req, result):
        print(result)
        self.rootwidget.clear_widgets()
        try:
            self.bus = json.loads(result)[0]["@attributes"]["cod"]
            self.bus_code = json.loads(result)[0]["terminal"]
            self.bus_distance = json.loads(result)[0]["stopdis"]
            self.bus_time = int(json.loads(result)[0]["time"])//60
            self.rootwidget.clear_widgets()
            info = "公交车牌照:{0}\n距离本站间隔:{1}\n距离本站时间(分钟):{2}".format(self.bus_code, self.bus_distance,
                                                                  str(self.bus_time))
            self.rootwidget.add_widget(BusStopInfo(self.data, self.busrouter_widget.bus_name_label.text,
                                                   self.busrouter_widget.bus_direction_name, info))
#            self.rootwidget.add_widget(ColorLabel(text=self.bus+self.bus_code+self.bus_distance+str(self.bus_time),
#                                                  font_name=new_font))
        except:
            self.errorcode = json.loads(result)["error"]
            if self.errorcode == "-2":
                print(dir(self.rootwidget))
                self.rootwidget.clear_widgets()
                info = "等待发车"
                self.rootwidget.add_widget(BusStopInfo(self.data, self.busrouter_widget.bus_name_label.text,
                                                       self.busrouter_widget.bus_direction_name, info))
#               self.rootwidget.add_widget(ColorLabel(text="等待发车", font_name=new_font))


class BusStopInfo(BoxLayout):
    stopinfotitle_label = ObjectProperty()
    stopinfobusname_label = ObjectProperty()
    stopinfobusdirection_label = ObjectProperty()
    stopinfoback_button = ObjectProperty()
    stopinfowatch_button = ObjectProperty()
    stopinfo_label = ObjectProperty()

    def __init__(self, data, bus_name, direction_name, info):
        super().__init__()
        self.stopinfotitle_label.text = "公交到站信息"
        self.stopinfotitle_label.font_name = new_font
        self.stopinfobusname_label.text = bus_name
        self.stopinfobusname_label.font_name = new_font
        self.stopinfobusdirection_label.text = direction_name
        self.stopinfobusdirection_label.font_name = new_font
        self.stopinfoback_button.text = "返回"
        self.stopinfoback_button.font_name = new_font
        self.stopinfowatch_button.text = "监控"
        self.stopinfowatch_button.font_name = new_font
        self.stopinfo_label.text = info
        self.stopinfo_label.font_name = new_font
        self.data = data

    def back_to_busrouter(self):
#        print(self.get_parent_window().children.add_widget)
        pass
    def add_to_watchlist(self):
        print("watched")







class ShanghaiBusApp(App):
    pass



if __name__ == "__main__":
    ShanghaiBusApp().run()