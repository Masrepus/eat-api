# -*- coding: utf-8 -*-

import requests
import re
from datetime import datetime
from lxml import html

import util
from entities import Dish, Menu


class MenuParser:
    def parse(self, location):
        pass


class StudentenwerkMenuParser(MenuParser):
    prices = {
        "Tagesgericht 1": 1, "Tagesgericht 2": 1.55, "Tagesgericht 3": 1.9, "Tagesgericht 4": 2.4,
        "Aktionsessen 1": 1.55, "Aktionsessen 2": 1.9, "Aktionsessen 3": 2.4, "Aktionsessen 4": 2.6,
        "Aktionsessen 5": 2.8, "Aktionsessen 6": 3.0, "Aktionsessen 7": 3.2, "Aktionsessen 8": 3.5, "Aktionsessen 9": 4,
        "Aktionsessen 10": 4.5, "Biogericht 1": 1.55, "Biogericht 2": 1.9, "Biogericht 3": 2.4, "Biogericht 4": 2.6,
        "Biogericht 5": 2.8, "Biogericht 6": 3.0, "Biogericht 7": 3.2, "Biogericht 8": 3.5, "Biogericht 9": 4,
        "Biogericht 10": 4.5, "Self-Service": "Self-Service"
    }
    links = {
        "mensa-garching": 'http://www.studentenwerk-muenchen.de/mensa/speiseplan/speiseplan_422_-de.html',
        "mensa-arcisstrasse": "http://www.studentenwerk-muenchen.de/mensa/speiseplan/speiseplan_421_-de.html",
        "stubistro-grosshadern": "http://www.studentenwerk-muenchen.de/mensa/speiseplan/speiseplan_414_-de.html"
    }

    def parse(self, location):
        page_link = self.links.get(location, "")
        if page_link != "":
            page = requests.get(page_link)
            tree = html.fromstring(page.content)
            return self.get_menus(tree)
        else:
            return None

    def get_menus(self, page):
        # initialize empty dictionary
        menus = {}
        # convert passed date to string
        # get all available daily menus
        daily_menus = self.__get_daily_menus_as_html(page)

        # iterate through daily menus
        for daily_menu in daily_menus:
            # get html representation of current menu
            menu_html = html.fromstring(html.tostring(daily_menu))
            # get the date of the current menu; some string modifications are necessary
            current_menu_date_str = menu_html.xpath("//strong/text()")[0]
            # parse date
            try:
                current_menu_date = util.parse_date(current_menu_date_str)
            except ValueError as e:
                print("Warning: Error during parsing date from html page. Problematic date: %s" % current_menu_date_str)
                # continue and parse subsequent menus
                continue
            # parse dishes of current menu
            dishes = self.__parse_dishes(menu_html)
            # create menu object
            menu = Menu(current_menu_date, dishes)
            # add menu object to dictionary using the date as key
            menus[current_menu_date] = menu

        # return the menu for the requested date; if no menu exists, None is returned
        return menus

    @staticmethod
    def __get_daily_menus_as_html(page):
        # obtain all daily menus found in the passed html page by xpath query
        daily_menus = page.xpath("//div[@class='c-schedule__item']")
        return daily_menus

    @staticmethod
    def __parse_dishes(menu_html):
        # obtain the names of all dishes in a passed menu
        dish_names = [dish.rstrip() for dish in menu_html.xpath("//p[@class='js-schedule-dish-description']/text()")]
        # make duplicates unique by adding (2), (3) etc. to the names
        dish_names = util.make_duplicates_unique(dish_names)
        # obtain the types of the dishes (e.g. 'Tagesgericht 1')
        dish_types = menu_html.xpath("//span[@class='stwm-artname']/text()")
        # create dictionary out of dish name and dish type
        dishes_dict = {dish_name: dish_type for dish_name, dish_type in zip(dish_names, dish_types)}
        # create Dish objects with correct prices; if price is not available, -1 is used instead
        dishes = [Dish(name, StudentenwerkMenuParser.prices.get(dishes_dict[name], -1)) for name in dishes_dict]
        return dishes

class FMIBistroMenuParser(MenuParser):
    allergens = ["Gluten", "Laktose", "Milcheiweiß", "Hühnerei", "Soja", "Nüsse", "Erdnuss", "Sellerie", "Fisch",
                 "Krebstiere", "Weichtiere", "Sesam", "Senf", "Milch", "Ei"]
    weekday_positions = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5}
    price_regex = r"\€\s\d+,\d+"
    dish_regex = r".+?\€\s\d+,\d+"

    def parse(self, location):
        # TODO
        return None

    def get_menus(self, text, year, week_number):
        menus = {}
        lines = text.splitlines()
        count = 0
        # remove headline etc.
        for line in lines:
            if line.replace(" ", "").replace("\n", "").lower() == "montagdienstagmittwochdonnerstagfreitag":
                break

            count += 1

        lines = lines[count:]
        # we assume that the weeksdays are now all in the first line
        pos_mon = lines[0].find("Montag")
        pos_tue = lines[0].find("Dienstag")
        pos_wed = lines[0].find("Mittwoch")
        pos_thu = lines[0].find("Donnerstag")
        pos_fri = lines[0].find("Freitag")

        lines_weekdays = {"mon": "", "tue": "", "wed": "", "thu": "", "fri": ""}
        for line in lines:
            lines_weekdays["mon"] += line[pos_mon:pos_tue].replace("\n", " ").replace("Montag", "")
            lines_weekdays["tue"] += line[pos_tue:pos_wed].replace("\n", " ").replace("Dienstag", "")
            lines_weekdays["wed"] += line[pos_wed:pos_thu].replace("\n", " ").replace("Mittwoch", "")
            lines_weekdays["thu"] += line[pos_thu:pos_fri].replace("\n", " ").replace("Donnerstag", "")
            lines_weekdays["fri"] += line[pos_fri:].replace("\n", " ").replace("Freitag", "")

        for key in lines_weekdays:
            # stop parsing day when bistro is closed at that day
            if "geschlossen" in lines_weekdays[key].lower():
                continue

            lines_weekdays[key] = lines_weekdays[key].replace("Allergene:", "")
            # remove multi-whitespaces
            lines_weekdays[key] = ' '.join(lines_weekdays[key].split())
            # remove allergnes
            for allergen in self.allergens:
                lines_weekdays[key] = lines_weekdays[key].replace(allergen, "")

            dish_names = re.findall(self.dish_regex, lines_weekdays[key])
            prices = re.findall(self.price_regex, ' '.join(dish_names))
            # convert prices to float
            prices = [float(price.replace("€", "").replace(",", ".").strip()) for price in prices]
            # remove price and commas
            dish_names = [re.sub(self.price_regex, "", dish).replace("," ,"").strip() for dish in dish_names]
            # create list of Dish objects
            dishes = [Dish(dish_name, price) for (dish_name, price) in list(zip(dish_names, prices))]
            # https://stackoverflow.com/questions/17087314/get-date-from-week-number
            date_str = "%d-W%d-%d" % (year, week_number, self.weekday_positions[key])
            date = datetime.strptime(date_str, "%Y-W%W-%w").date()
            menu = Menu(date, dishes)
            menus[date] = menu

        return menus
