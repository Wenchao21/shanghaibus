#	-- coding:utf-8 --
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import ObjectProperty
from kivy.network.urlrequest import UrlRequest
from bs4 import BeautifulSoup
from xpinyin import Pinyin

bus_list = []
bus_dict = {}
query_router_url = 'http://shanghaicity.openservice.kankanews.com/public/bus'


def get_bus_list():
	req = UrlRequest(query_router_url,on_success=parse_bus_list)

def parse_bus_list(req, result):
	global bus_list
	soup = BeautifulSoup(result, "html.parser")
	for line in soup.find_all("script")[2]:
		if "var data = " in line:
			bus_list = line.split("[")[1].split("];")[0].split(",")
	print(bus_list)
	p = Pinyin()
	bus_dict = {p.get_initials(x, ""):x for x in bus_list}
	print(bus_dict)
	with open("buslist.txt", "w") as f:
		f.write(str(bus_dict))








kivy.resources.resource_add_path(r"C:\Windows\Fonts")
new_font = kivy.resources.resource_find("DroidSansFallback.ttf")


class RootWidget(BoxLayout):
	pass

class QueryStation(BoxLayout):
	search_button = ObjectProperty()
	def	change_font(self):
		self.search_button.text = "中文"
		self.search_button.font_name = new_font
		get_bus_list()

	pass




class ShanghaiBusApp(App):
	pass



if __name__ == "__main__":
	ShanghaiBusApp().run()