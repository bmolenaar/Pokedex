import kivy
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.screenmanager import SlideTransition
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image, AsyncImage
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
Clock.max_iteration = 152
from kivy.properties import StringProperty,NumericProperty,ListProperty
from kivy.graphics import Rectangle, Color
import time
import certifi
import os
import threading
from functools import partial
import asyncio
from aiohttp_client_cache import CachedSession, SQLiteBackend

BASE_URL = "https://pokeapi.co/api/v2/pokemon/"
NUM_POKES = 152
os.environ['SSL_CERT_FILE'] = certifi.where()
#requests_cache.install_cache('poke_cache', backend='sqlite')
start_time = time.time()

async def query_api(urls):
	now = time.ctime(int(time.time()))
	result = []
	#async with aiohttp.ClientSession() as session:
	async with CachedSession(cache=SQLiteBackend('poke_cache', expire_after=86400)) as session:
		for u in urls:
			async with session.get(u) as resp:
				pokemon = await resp.json()
				result.append(pokemon)

	print("--- %s seconds ---" % (time.time() - start_time))
	return(result)


def make_list():
	urls  = []
	for p in range(NUM_POKES):
		if p != 0:
			url = '{0}{1}'.format(BASE_URL, str(p))
			urls.append(url)
	return urls


def remove_dupes(x):
	return list(dict.fromkeys(x))

def get_pokemon_id(data):
	pokeId = data
	if pokeId  < 10:
		pokeId = '{0}{1}'.format('00',str(pokeId))
	elif pokeId > 9 and pokeId < 100:
		pokeId = str(0) + str(pokeId)
		
	return str(pokeId)

def get_pokemon_types(data):
	allTypes = data
	types = []
	
	for r in allTypes:
		types.append(r['type']['name'])
	
	if len(types) < 2:
		pokeType = types[0]
	else:
		pokeType = str(types[0] + "/" + types[1])
	
	return pokeType

def get_pokemon_abilities(data):
	allAbilities = data
	abilities  = []
				
	for a in allAbilities:
		ability =  a['ability']['name'].replace('-','  ')
		abilities.append(ability)
	
	if len(abilities) == 1:
		pokeAbility =  abilities[0]
	elif len(abilities) == 2:
		pokeAbility = (abilities[0] + "/" + abilities[1])
	else:
		pokeAbility = (abilities[0] + "/" + abilities[1] + "/" + abilities[2])
	
	return pokeAbility


def return_pokemon(self):
	pokes = []
	for i in range(NUM_POKES):
		if i != 0:
			pokes.append(i)
		
	return pokes

async def get_pokemon_dex_entry(data):
	pokemon = data.lower()
	url = 'https://pokeapi.co/api/v2/pokemon-species/{0}'.format(str(pokemon))
	result = []
	
	async with CachedSession(cache=SQLiteBackend('poke_cache2', expire_after=86400)) as session:
		async with session.get(url) as resp:
			data = await resp.json()
			dexEntry = data['flavor_text_entries'][0]['flavor_text'].replace('\n', ' ')
			dexEntry = dexEntry.replace('\f', '\n')
			species = data['genera'][7]['genus']
			result.append(dexEntry)
			result.append(species)
			
	return result

async def get_pokemon_weaknessess(data):
	types = get_pokemon_types(data['types']).split('/')
	weaknesses = []
	resists = []
	toRemove = []
	matchups = []
	immunities = []
	
	for t in types:
		url = 'https://pokeapi.co/api/v2/type/{0}'.format(t)
		async with CachedSession(cache=SQLiteBackend('poke_cache3', expire_after=86400)) as session:
			async with session.get(url) as resp:
				result = await resp.json()
				for r in result['damage_relations']['double_damage_from']:
					weaknesses.append(r['name'])
				for s in result['damage_relations']['half_damage_from']:
					resists.append(s['name'])
				for n in result['damage_relations']['no_damage_from']:
					immunities.append(n['name'])
	
	weaknesses = remove_dupes(weaknesses)
	resists = remove_dupes(resists)
	
	for w in weaknesses:
		for r in resists:
			if w == r:
				toRemove.append(w)
			
	for item in toRemove:
		weaknesses.remove(item)
		resists.remove(item)
	
	for i in immunities:
		for w in weaknesses:
			if i == w:
				weaknesses.remove(i)

	allWeakness = ' '.join(weaknesses)
	allResists = ' '.join(resists)
	
	matchups.append(allWeakness.upper())
	matchups.append(allResists.upper())
	return matchups

class MenuScreen(Screen):
    Builder.load_string("""
<MenuScreen>:
    BoxLayout:
        Button:
            text: 'Go to dex'
            on_press: root.manager.current = 'dex'
        Button:
            text: 'Quit'
		""")

class LabelWithBackground(Label):

    def __init__(self, bgcolor, **kwargs):
        super().__init__(**kwargs)
        self.bgcolor = bgcolor
        self.draw_background()

    def draw_background(self):
        if self.canvas is not None:
            self.canvas.before.clear()
            with self.canvas.before:
                Color(*self.bgcolor)
                Rectangle(pos=self.pos, size=self.size)

    def on_size(self, *args):
        self.draw_background()

    def on_pos(self, *args):
        self.size = self.texture_size
        self.draw_background()
	
class PokeScreen(Screen):
	
	dexNum = StringProperty('')
	pokeName  = StringProperty('')
	bannerTxt = StringProperty('')
	species = ListProperty([])
	dexEntry = StringProperty('')
	pokeHeight = StringProperty('')
	category = StringProperty('')
	pokeWeight = StringProperty('')
	abilities = StringProperty('')
	hp = StringProperty('')
	attack  = StringProperty('')
	defence = StringProperty('')
	spattack = StringProperty('')
	spdefence = StringProperty('')
	speed = StringProperty('')
	typechart = ListProperty([])
	weakness = StringProperty('')
	resistances = StringProperty('')
	
	
	def __init__(self, poke, **kwargs):
		super(PokeScreen, self).__init__(**kwargs)
		Window.clearcolor = (1, 1, 1, 1)
		
		self.dexNum = get_pokemon_id(poke['id'])
		self.pokeName = poke['name'].upper()
		self.bannerTxt = self.pokeName + ' ' + '#' + self.dexNum
		self.species = asyncio.run(get_pokemon_dex_entry(self.pokeName))
		self.dexEntry = self.species[0]
		self.pokeHeight = str(int(poke['height']) * 10) + 'cm'
		self.category = self.species[1]
		self.pokeWeight = str(int(poke['weight']) / 10) + 'kg'
		self.abilities = get_pokemon_abilities(poke['abilities'])
		self.abilities = self.abilities.replace('/', '\n')
		self.hp = str(poke['stats'][0]['base_stat'])
		self.attack = str(poke['stats'][1]['base_stat'])
		self.defence = str(poke['stats'][2]['base_stat'])
		self.spattack = str(poke['stats'][3]['base_stat'])
		self.spdefence = str(poke['stats'][4]['base_stat'])
		self.speed = str(poke['stats'][5]['base_stat'])
		
		self.toSplit = str(poke['sprites']['other']['official-artwork'])
		self.start = self.toSplit.index(':') + 3
		self.end = self.toSplit.index('.png') + 4
		self.path = str(self.toSplit[self.start:self.end])
		
		self.typechart = asyncio.run(get_pokemon_weaknessess(poke))
		self.weakness = self.typechart[0]
		self.resistances = self.typechart[1]
		
		self.create()
	

	def btnpress(self, instance):
		sm.remove_widget(self)
		sm.current = 'dex'
	
	def create(self, **args):
		self.scrollbar = ScrollView()
		self.scrollbar.size_hint_y = 1

		self.floater = FloatLayout()
		self.floater.size_hint_y = 0.9
		self.add_widget(self.scrollbar)
		self.scrollbar.add_widget(self.floater)
		
		#Back button, Name and ID at the top of screen
		self.banner = GridLayout(pos_hint={'top':1})
		self.banner.cols = 2
		self.banner.rows = 1
		self.banner.size_hint_y = 0.1
		self.floater.add_widget(self.banner)

		self.banner.add_widget(Button(background_normal='back.png', size_hint=(0.2,0.2), on_press=self.btnpress))
		self.banner.add_widget(LabelWithBackground(font_size=30, text=str(self.bannerTxt), color=(1, 1, 1, 1), bgcolor=(0, 0, 0, 1)))
		
		#Sprite
		self.topthird = GridLayout(pos_hint={'top':0.9})
		self.topthird.cols = 2
		self.topthird.rows = 2
		self.topthird.spacing = 1
		self.floater.add_widget(self.topthird)		
		self.topthird.add_widget(AsyncImage(source=str(self.path)))
		
		#Dex Entry, Versions and info
		self.details = GridLayout()
		self.details.cols = 1
		self.details.rows  = 3
		self.details.spacing = 1
		self.topthird.add_widget(self.details)
		self.details.add_widget(LabelWithBackground(text=self.dexEntry, bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		#self.details.add_widget(LabelWithBackground(text='Placeholder for version changer', bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		
		self.info = GridLayout()
		self.info.cols = 2
		self.info.rows =  2
		self.info.spacing = 1
		self.details.add_widget(self.info)
		
		self.info.add_widget(LabelWithBackground(text=str(self.pokeHeight), bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		self.info.add_widget(LabelWithBackground(text=str(self.category), bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		self.info.add_widget(LabelWithBackground(text=self.pokeWeight, bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		self.info.add_widget(LabelWithBackground(text=str(self.abilities), bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		
		#Stats
		self.stats = GridLayout()
		self.stats.cols = 2
		self.stats.rows = 3
		self.stats.spacing = 1
		self.topthird.add_widget(self.stats)
		
		self.statgrid =  GridLayout()
		self.statgrid.cols = 1
		self.statgrid.rows = 2
		
		self.statgrid1 =  GridLayout()
		self.statgrid1.cols = 1
		self.statgrid1.rows = 2
		
		self.statgrid2 =  GridLayout()
		self.statgrid2.cols = 1
		self.statgrid2.rows = 2
		
		self.statgrid3 =  GridLayout()
		self.statgrid3.cols = 1
		self.statgrid3.rows = 2
		
		self.statgrid4 =  GridLayout()
		self.statgrid4.cols = 1
		self.statgrid4.rows = 2
		
		self.statgrid5 =  GridLayout()
		self.statgrid5.cols = 1
		self.statgrid5.rows = 2

		self.stats.add_widget(self.statgrid)
		self.statgrid.add_widget(LabelWithBackground(text='HP', bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		self.statgrid.add_widget(LabelWithBackground(text=self.hp, bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		
		self.stats.add_widget(self.statgrid1)
		self.statgrid1.add_widget(LabelWithBackground(text='ATTACK', bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		self.statgrid1.add_widget(LabelWithBackground(text=self.attack, bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		
		self.stats.add_widget(self.statgrid2)
		self.statgrid2.add_widget(LabelWithBackground(text='DEFENCE', bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		self.statgrid2.add_widget(LabelWithBackground(text=self.defence, bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		
		self.stats.add_widget(self.statgrid3)
		self.statgrid3.add_widget(LabelWithBackground(text='SP.ATTACK', bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		self.statgrid3.add_widget(LabelWithBackground(text=self.spattack, bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		
		self.stats.add_widget(self.statgrid4)
		self.statgrid4.add_widget(LabelWithBackground(text='SP.DEFENCE', bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		self.statgrid4.add_widget(LabelWithBackground(text=self.spdefence, bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		
		self.stats.add_widget(self.statgrid5)
		self.statgrid5.add_widget(LabelWithBackground(text='SPEED', bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))
		self.statgrid5.add_widget(LabelWithBackground(text=self.speed, bgcolor=(1, 0.87, 0, 1), color=(0,0,0,1)))

		
		#Weaknessess/Resistances
		self.matchups = GridLayout()
		self.matchups.cols = 1
		self.matchups.rows = 2
		self.matchups.spacing = 1
		self.topthird.add_widget(self.matchups)
		
		self.matchupgrid = GridLayout()
		self.matchupgrid.cols = 1
		self.matchupgrid.rows = 2
		self.matchups.add_widget(self.matchupgrid)
		self.matchupgrid.add_widget(LabelWithBackground(text='Weaknessess', bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		self.matchupgrid.add_widget(LabelWithBackground(text=self.weakness, bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		
		self.matchupgrid1 = GridLayout()
		self.matchupgrid1.cols = 1
		self.matchupgrid1.rows = 2
		self.matchups.add_widget(self.matchupgrid1)
		self.matchupgrid1.add_widget(LabelWithBackground(text='Resistances', bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))
		self.matchupgrid1.add_widget(LabelWithBackground(text=self.resistances, bgcolor=(59 / 255, 76 / 255, 202 / 255, 1)))



class MyGrid(Screen):
	
	def __init__(self, **kwargs):
		
		super(MyGrid, self).__init__(**kwargs)
		Window.clearcolor = (0, 0, 0, 1)
		t1 = threading.Thread(target=self.loading)
		t2 = threading.Thread(target=self.doAll)
		t1.start()
		t2.start()
		t1.join()

		
	def loading(self, **args):
		
		self.loadgrid = GridLayout()
		self.loadgrid.rows = 2
		self.loadgrid.cols = 1
		
		self.loadtext = Label(font_size=50, text='LOADING...')
		#self.loadgif = AsyncImage(source='https://i.pinimg.com/originals/f9/7f/5c/f97f5c6510994f677877b08320475008.gif',anim_delay=0.25,keep_data = True)
		self.loadgif = AsyncImage(source='images.zip',anim_delay=0.45)
		
		self.loadgrid.add_widget(self.loadtext)
		self.loadgrid.add_widget(self.loadgif)
		self.add_widget(self.loadgrid)
		
	
	def btnPress(self, pokemon, instance):
		sm.add_widget(PokeScreen(pokemon, name='details'))
		sm.current = 'details'
	
	def doAll(self, **args):
		
		self.scroller = ScrollView()
		
		self.outside = FloatLayout()
		self.outside.size_hint_y = 30
		
		self.add_widget(self.scroller)
		self.scroller.add_widget(self.outside)
		
		self.inside = GridLayout()
		self.inside.cols = 2
		self.outside.add_widget(self.inside)
		
		self.inner  = GridLayout()
		self.inner.cols = 2
		self.outside.add_widget(self.inner)
		
		urls = make_list()
		pokemon = asyncio.run(query_api(urls))
		
		
		for p in pokemon:
			if p is not None:

				data = p
				
				self.pokegrid  = GridLayout()
				self.pokegrid.cols = 2
				self.pokegrid.size_hint = (1.9, 1.9)
				
				imgButton = Button(size_hint=(0.3,0.3), background_color=(51,23,186,1))
				btncallback = partial(self.btnPress, data)
				imgButton.bind(on_press=btncallback)
				
				dataButton = Button(background_color=(255,0,0,1))
				dataButton.bind(on_press=btncallback)
				
				self.inside.add_widget(imgButton)
				self.inside.add_widget(dataButton)
				
				toSplit = str(data['sprites']['other']['official-artwork'])
				start = toSplit.index(':') + 3
				end = toSplit.index('.png') + 4
				path = str(toSplit[start:end])

				self.inner.add_widget(AsyncImage(source=str(path), size_hint_x=0.5))
				self.inner.add_widget(self.pokegrid)
				
				self.pokegrid.add_widget(Label(font_size=30, text=str(get_pokemon_id(data['id']))))
				self.pokegrid.add_widget(Label(font_size=50, text=str(data['name'])))											
				self.pokegrid.add_widget(Label(font_size=30, text=str(get_pokemon_types(data['types']))))
				self.pokegrid.add_widget(Label(font_size=30, text=str(get_pokemon_abilities(data['abilities']))))
		
		self.remove_widget(self.loadgrid)

sm =  ScreenManager(transition=SlideTransition())
sm.add_widget(MenuScreen(name='menu'))
sm.add_widget(MyGrid(name='dex'))

class MyMainApp(App):
	def build(self):
		return (sm)

if __name__ == "__main__":
	MyMainApp().run()
