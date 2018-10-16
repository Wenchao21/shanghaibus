#    -- coding:utf-8 --

import kivy
from kivy.storage.jsonstore import JsonStore
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
from kivy.clock import Clock
import time


store = JsonStore("info.json")
watch_stations = JsonStore("watchlist.json")
query_router_url = 'https://shanghaicity.openservice.kankanews.com/public/bus'
query_bus_sid = "https://shanghaicity.openservice.kankanews.com/public/bus/get"
query_bus_router = "https://shanghaicity.openservice.kankanews.com/public/bus/mes/sid/"
query_bus_stop = "https://shanghaicity.openservice.kankanews.com/public/bus/Getstop"

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


class LoadingScreen(BoxLayout):
    pass


class NetworkCheckScreen(BoxLayout):
    network_check_label = ObjectProperty()

    def __init__(self, info):
        super().__init__()
        self.network_check_label.text = info
        self.network_check_label.font_name = new_font


class ErrorScreen(BoxLayout):
    error_info_label = ObjectProperty()

    def __init__(self, info):
        super().__init__()
        self.error_info_label.text = info
        self.error_info_label.font_name = new_font


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
        self.rootwidget.add_widget(LoadingScreen())

    def get_bus_router(self):
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Accept': 'text/plain'}
        params = urllib.parse.urlencode({"idnum": self.cbusname})
        req = UrlRequest(query_bus_sid, on_success=self.parse_bus_id, req_body=params, on_error=self.print_error,
                         method="POST", req_headers=headers, on_failure=self.print_failure)

    def print_error(self, req, error):
        try:                                                  # 回调函数中无法直接使用get_parent_window(), get_root_window()
            if error.strerror == 'getaddrinfo failed':        # 回调函数延时执行，可能主窗口没有被渲染， 返回值为None
                self.rootwidget.clear_widgets()
                self.rootwidget.add_widget(NetworkCheckScreen("请检查你的网络"))
        except:
            self.rootwidget.clear_widgets()
            self.rootwidget.add_widget(NetworkCheckScreen(str(error)))

    def parse_bus_id(self, req, result):
        self.sid = result.get("sid")
        for i in [0, 1]:
            url = "{0}/{1}?stoptype={2}".format(query_bus_router, self.sid, i)
            if i == 0:
                request = UrlRequest(url, on_success=self.parse_bus_router, on_error=self.print_error,
                                     on_failure=self.print_failure)
            else:
                request = UrlRequest(url, on_success=self.parse_bus_router_reverse, on_error=self.print_error,
                                     on_failure=self.print_failure)

    def print_failure(self, req, result):
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(ErrorScreen(str(result)))

    def parse_bus_router(self, req, result):
        selector = etree.HTML(result)
        ftolstation = selector.xpath("//div[@class='upgoing cur ' or @class='upgoing ']/p/span/text()")
        ftoltime = selector.xpath("//div[@class='upgoing cur ' or @class='upgoing ']/div/em/text()")
        print("ftol", ftolstation, ftoltime)
        for i in [0, 2]:
            self.ftolinfo.append("{0}-->{1}    首班车:{2}  末班车{3}".format(ftolstation[i], ftolstation[i+1],
                                                                       ftoltime[i], ftoltime[i+1]))
        bus_stations_temp = selector.xpath("//span[@class='name']/text()")
        self.bus_stations = ["{0}.{1}".format(i+1, bus_stations_temp[i])for i in range(len(bus_stations_temp))]
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(BusRouter(self.cbusname, self.ftolinfo, self.bus_stations,
                                             self.bus_stations_reverse, self.sid))
        store.put("cbusname", value=self.cbusname)
        store.put("ftolinfo", value=self.ftolinfo)
        store.put("bus_stations", value=self.bus_stations)
        store.put("bus_stations_reverse", value=self.bus_stations_reverse)
        store.put("sid", value=self.sid)

    def parse_bus_router_reverse(self, req, result):
        selector = etree.HTML(result)
        bus_stations_reverse_temp = selector.xpath("//span[@class='name']/text()")
        self.bus_stations_reverse = \
            ["{0}.{1}".format(i+1, bus_stations_reverse_temp[i]) for i in range(len(bus_stations_reverse_temp))]
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(BusRouter(self.cbusname, self.ftolinfo, self.bus_stations,
                                             self.bus_stations_reverse, self.sid))
        store.put("cbusname", value=self.cbusname)
        store.put("ftolinfo", value=self.ftolinfo)
        store.put("bus_stations", value=self.bus_stations)
        store.put("bus_stations_reverse", value=self.bus_stations_reverse)
        store.put("sid", value=self.sid)

    def return_data(self):
        return self.cbusname, self.ftolinfo, self.bus_stations, self.bus_stations_reverse, self.sid


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
        rootwidget.add_widget(RootWidget())


class BusDirection(ListItemButton):
    def __init__(self, **kwargs):
        super(BusDirection, self).__init__(**kwargs)

    def change_bus_direction(self):
        rootwidget = self.get_parent_window().children[0]
        busrouter_widget = rootwidget.children[0]
        busrouter_widget.bus_direction_name = self.text
        if self.index == 1:
            render_listbutton(busrouter_widget.bus_station_listbutton, busrouter_widget.bus_stations_reverse)
            busrouter_widget.bus_direction = 1
            store.put("bus_direction", vaule=1)
        elif self.index == 0:
            render_listbutton(busrouter_widget.bus_station_listbutton, busrouter_widget.bus_stations)
            busrouter_widget.bus_direction = 0
            store.put("bus_direction", value=0)


class BusStation(ListItemButton):
    def query_stop_info(self):
        self.rootwidget = self.get_parent_window().children[0]
        self.busrouter_widget = self.rootwidget.children[0]
        self.direction = self.busrouter_widget.bus_direction
        sid = self.busrouter_widget.sid
        self.stop_station_name = self.text.split(".")[1]
        stopid = self.text.split(".")[0]
        self.data = {"stoptype": self.direction, "stopid": stopid, "sid": sid}
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Accept': 'text/plain'}
        req = UrlRequest(query_bus_stop, req_headers=headers, req_body=urllib.parse.urlencode(self.data),
                         on_success=self.parse_stop_info)
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(LoadingScreen())

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
                                                   self.busrouter_widget.ftolinfo[self.direction], info,
                                                   self.stop_station_name))
        except:
            self.errorcode = json.loads(result)["error"]
            if self.errorcode == "-2":
                self.rootwidget.clear_widgets()
                info = "等待发车"
                self.rootwidget.add_widget(BusStopInfo(self.data, self.busrouter_widget.bus_name_label.text,
                                                       self.busrouter_widget.ftolinfo[self.direction], info,
                                                       self.stop_station_name))


class BusStopInfo(BoxLayout):
    stopinfotitle_label = ObjectProperty()
    stopinfobusname_label = ObjectProperty()
    stopinfobusdirection_label = ObjectProperty()
    stopinfoback_button = ObjectProperty()
    stopinfowatch_button = ObjectProperty()
    stopinfo_label = ObjectProperty()

    def __init__(self, data, bus_name, direction_name, info, stop_station_name):
        super().__init__()
        self.stopinfotitle_label.text = "公交到站信息"
        self.stopinfotitle_label.font_name = new_font
        self.stopinfobusname_label.text = bus_name + " " * 4 + stop_station_name
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
        self.rootwidget = self.get_parent_window().children[0]
        self.rootwidget.clear_widgets()
        self.rootwidget.add_widget(BusRouter(store.get("cbusname")["value"], store.get("ftolinfo")["value"],
                                             store.get("bus_stations")["value"],
                                             store.get("bus_stations_reverse")["value"],
                                             store.get("sid")["value"]))
        pass

    def add_to_watchlist(self):
        with open("refresh_info.json", "r") as f:
            refresh_data = json.load(f)
        with open("watchlist.json", "r") as f:
            original_data = json.load(f)
        storeinfo = self.stopinfobusname_label.text + " " * 4 + self.stopinfobusdirection_label.text.split(" ")[0]
        original_data[storeinfo] = {"value": storeinfo, "data": self.data, "offset_station": "3", "offset_time": "5",
                                    "watched": True, "start_time": "0000", "end_time": "2400"}
        with open("watchlist.json", "w") as f:
            json.dump(original_data, f)
        key = storeinfo
        try:
            station_offset = self.stopinfo_label.text.split("\n")[1].split(":")[1]
            time_offset = self.stopinfo_label.text.split("\n")[2].split(":")[1]
            value = "距离本站还有{0}站  距离本站还有:{1}分钟".format(station_offset, time_offset)
        except:
            value = self.stopinfo_label.text
        finally:
            refresh_data[key] = value
            with open("refresh_info.json", "w") as f:
                json.dump(refresh_data, f)
        rootwidget = self.get_parent_window().children[0]
        rootwidget.clear_widgets()
        rootwidget.add_widget(WatchListWidget())


class MenuButton(BoxLayout):
    menu_query = ObjectProperty()
    menu_watch = ObjectProperty()
    menu_about = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._finish_init)

    def _finish_init(self, unknown):                      # 为什么需要两个参数？
        self.menu_query.text = "查询界面"
        self.menu_query.font_name = new_font
        self.menu_watch.text = "监控站点列表"
        self.menu_watch.font_name = new_font
        self.menu_about.text = "关于"
        self.menu_about.font_name = new_font

    def to_query(self):
        print("query")
        rootwidget = self.get_parent_window().children[0]
        rootwidget.clear_widgets()
        rootwidget.add_widget(RootWidget())

    def to_watch(self):
        rootwidget = self.get_parent_window().children[0]
        rootwidget.clear_widgets()
        rootwidget.add_widget(WatchListWidget())

    def to_about(self):
        rootwidget = self.get_parent_window().children[0]
        rootwidget.clear_widgets()
        rootwidget.add_widget(AboutWidget())


class AboutWidget(BoxLayout):
    about_info = ObjectProperty()
    update = ObjectProperty()

    def __init__(self):
        super().__init__()
        self.about_info.text = "查询数据来自源上海发布\n作者：吕超\n邮箱：lc1923@live.cn\n"
        self.about_info.font_name = new_font
        self.update.text = "更新公交列表"
        self.update.font_name = new_font

    def update_buslist(self):
        print("BusList updated")


class WatchListWidget(BoxLayout):
    watch_list_label = ObjectProperty()
    station_watch_list = ObjectProperty()

    def __init__(self):
        super().__init__()
        WatchinfoRefresh(time=1)
        Clock.schedule_once(self.render_widget)
        Clock.schedule_interval(self.render_widget, 5)

    def refresh_file_change(self):
        with open("refresh_info.json", "r") as f:
            origin_data = json.load(f)
        time.sleep(5)
        with open("refresh_info.json", "r") as f:
            new_data = json.load(f)
        if origin_data != new_data:
            Clock.schedule_once(self.render_widget)

    def render_widget(self, dt):
        render_list = []
        self.watch_list_label.text = "站点列表"
        self.watch_list_label.font_name = new_font
        watch_stations = JsonStore("watchlist.json")                  # 重新获取json文件内容，否则新增站点不能即刻刷新出来
        with open("refresh_info.json", "r") as f:
            data = json.load(f)
        print("+++++++++++++++++++++++++++++++++++++")
        print(data)
        for i in watch_stations.keys():
            if "Thread" in data[i]:
                data[i] = "数据查询中..."
            render_list.append("{0}{1}{2}".format(i, " "*4+"|"+" "*4, data[i]))
        # render_list = watch_stations.keys()
        render_listbutton(self.station_watch_list, render_list)


class StationWatchList(ListItemButton):
    def show_watch_station(self):
        rootwidget = self.get_parent_window().children[0]
        text = self.text.split("|")[0].strip()
        rootwidget.clear_widgets()
        rootwidget.add_widget(WatchedStation(text))


class WatchedStation(BoxLayout):
    watched_station_title_label = ObjectProperty()
    watched_station_info_label = ObjectProperty()
    watched_offset_station_label = ObjectProperty()
    watched_offset_station_textinput = ObjectProperty()
    watched_offset_time_label = ObjectProperty()
    watched_offset_time_textinput = ObjectProperty()
    check_option_label = ObjectProperty()
    check_option_checkbox = ObjectProperty()
    watched_time_label = ObjectProperty()
    start_hour_textinput = ObjectProperty()
    start_min_textinput = ObjectProperty()
    end_hour_textinput = ObjectProperty()
    end_min_textinput = ObjectProperty()
    delete_button = ObjectProperty()

    def __init__(self, station_name):
        super().__init__()
        # with open("watchlist.json", "r") as f:
        #     data = json.load(f)
        # print(station_name)
        # print(data.keys())
        # print(station_name in data.keys())
        # print(self.watched_offset_station_textinput.text)
        # print(data[station_name]["offset_station"])
        # if self.watched_station_info_label.text in data.keys():
        #     print(data[self.watched_station_info_label.text]["offset_station"])
        #     self.watched_offset_station_textinput.text = data[station_name]["offset_station"]
        self.jsonitem = station_name
        watch_stations = JsonStore("watchlist.json")
        self.watched_offset_station_textinput.text = watch_stations.get(station_name)["offset_station"]
        self.watched_station_title_label.text = "监控站点"
        self.watched_station_title_label.font_name = new_font
        self.watched_station_info_label.text = station_name
        self.watched_station_info_label.font_name = new_font
        self.watched_offset_station_label.text = "距离站点数："
        self.watched_offset_station_label.font_name = new_font
        self.watched_offset_time_label.text = "距离站点时间(分钟)："
        self.watched_offset_time_label.font_name = new_font
        self.check_option_label.text = "是否监控："
        self.check_option_label.font_name = new_font
        self.watched_time_label.text = "监控时间："
        self.watched_time_label.font_name = new_font
        self.delete_button.text = "删除"
        self.delete_button.font_name = new_font

    def offset_station_input(self):
        with open("watchlist.json", "r") as f:
            original_data = json.load(f)
        original_data[self.jsonitem]["offset_station"] = \
            self.watched_offset_station_textinput.text
        with open("watchlist.json", "w") as f:
            json.dump(original_data, f)

    def delete_station(self):
        with open("watchlist.json", "r") as f:
            original_data = json.load(f)
        del original_data[self.watched_station_info_label.text]
        with open("watchlist.json", "w") as f:
            json.dump(original_data, f)
        rootwidget = self.get_parent_window().children[0]
        rootwidget.clear_widgets()
        rootwidget.add_widget(WatchListWidget())


class WatchinfoRefresh():
    name_req_dict = {}
    req_result_dict = {}

    def __init__(self, time=60):
        self.time = time
        if self.time == 60:
            self.refresh_cycle()
        else:
            self.refresh_once()

    def refresh_cycle(self):
        Clock.schedule_interval(self.watchinfo_refresh, 60)

    def refresh_once(self):
        Clock.schedule_once(self.watchinfo_refresh)

    def watchinfo_refresh(self, dt):
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Accept': 'text/plain'}
        # dt函数定义需要的参数
        with open("watchlist.json", "r") as f:
            data = json.load(f)
        for i in data.keys():
            self.playload = {"stoptype": data[i]["data"]["stoptype"], "stopid": data[i]["data"]["stopid"],
                        "sid": data[i]["data"]["sid"]}
            req = UrlRequest(query_bus_stop, req_headers=headers, req_body=urllib.parse.urlencode(self.playload),
                             on_success=self.parse_stop_info)
            WatchinfoRefresh.name_req_dict[i] = req.name

    def parse_stop_info(self, req, result):
        try:
            self.bus_distance = json.loads(result)[0]["stopdis"]
            self.bus_time = int(json.loads(result)[0]["time"])//60
            info = "距离本站还有{0}站  距离本站还有:{1}分钟".format(self.bus_distance, str(self.bus_time))
        except:
            self.errorcode = json.loads(result)["error"]
            if self.errorcode == "-2":
                info = "等待发车"
        finally:
            for i in WatchinfoRefresh.name_req_dict.keys():
                if req.name == WatchinfoRefresh.name_req_dict[i]:
                    WatchinfoRefresh.name_req_dict[i] = info
            print(WatchinfoRefresh.name_req_dict)
            with open("refresh_info.json", "w") as f:
                json.dump(WatchinfoRefresh.name_req_dict, f)
            list_refresh = WatchListWidget()


class ShanghaiBusApp(App):
    pass


if __name__ == "__main__":
    s = WatchinfoRefresh()
    s.refresh_cycle()
    ShanghaiBusApp().run()
