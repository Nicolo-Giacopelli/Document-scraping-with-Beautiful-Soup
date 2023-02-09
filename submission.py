from bs4 import BeautifulSoup
import re 
import os
import datetime
import json
import time

startTime = time.time()

# regular expressions used to filter the scraped data, with contact info shared between restaurant and customer
parse_address = re.compile(r"^\d+,?[a-zA-Z\u00C0-\u017F\s'-]*")  # start with digits, comma (in case), then only alphabetic characters including non-ASCII ones (accented letters)
parse_city = re.compile(r"[\D]+") 
parse_postcode = re.compile(r"\d+")  # only digits with no constraint on number
parse_phone = re.compile(r"(\+33|0)[\d\s]+\d")  # start with either +33 or 0, then all numbers/spaces and end with number
parse_cost = re.compile(r"\d+.\d+")  # frais de livraison and total
parse_q = re.compile(r"^\d+")  # quantity of item 
parse_p = re.compile(r"^\d+,\d+")  # price of item
parse_t = re.compile(r".+")  # captures everything, used for item name
parser_contact = [parse_t, parse_address, parse_city, parse_postcode, parse_phone] # list of parser for contact info

# list comprising keys of dictionary, used to create and loop through them
keys_fin = ["order", "restaurant", "customer", "order_items"]
keys_contact = ["name", "address", "city", "postcode", "phone_number"]  
keys_items = ["name", "quantity", "price"]

# list and dictionary used for datetime retrieval
month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
dic = {k:v+1 for (v, k) in enumerate(month)}

# function to retrieve all contact info for both restaurant and customer
def restaurant_and_customer(soup):
    restaurant, customer = dict(), dict()  # stores
    fluids = soup.find_all("table", attrs = {"class": "fluid", "width": "200"})  # index 0 is restaurant info, index 1 is customer info
    for index, store in enumerate([restaurant, customer]):
        thresh = fluids[index].find("p")  # we start from the first paragraph and search the next one recursively inside the loop
        for key, parse in zip(keys_contact, parser_contact):  
            data = thresh.get_text(strip = True)
            parsed = parse.match(data)  # loop through the (two) tables and parsing the data
            if parsed:      # creating the key only upon existence
                store[key] = parsed.group(0).strip()
            thresh = thresh.find_next("p")
        if "address" in store.keys():  # string manipulation for address (remove name of the city, postcode already filtered out with regex)
            store["address"] = store["address"].replace(str(store["city"]), "").replace(',', '').strip(' ,.-')
        if "phone_number" in store.keys():  # string manipulation for phone number, all starting from 0
            store["phone_number"] = re.sub(" ", "", store["phone_number"]).replace("+33", "0")
    return restaurant, customer  # returns the two dictionaries  

# function to retrieve the datetime
def get_date(email, store):
    full_str = os.path.splitext(email.name)[0]   # we get name of file without extension
    date = []
    for piece in full_str.split("_")[:-1]:
        date.append(piece)
    store["order_datetime"] = datetime.datetime(int(date[3]), dic.get(date[2]), int(date[1]),
                             int(date[4]), int(date[5]), int(date[6])).strftime("%Y-%m-%d %H:%M:%S") # printed and formatted from datetime object
    return store    # return updated order information with retrieved datetime

# function to retrieve all order information (also calling the above)
def order(soup, email):
    order = dict()
    order = get_date(email, order) 
    ## order_number ##
    number = soup.find_all("h2", attrs = {"class": "vmarg16x"})[2].text
    order_number = parse_postcode.search(number).group(0)   # we match all the numbers as with postcode, kept as string
    if order_number:   # creation of key upon existence
        order["order_number"] = order_number
    ## delivery fee ##
    frais = soup.find("p", string = re.compile(r"Frais de livraison"))
    if frais:   # creation of key if html tag is found
        cost = frais.find_next('p').get_text(strip = True).replace('Free', '0.0')
        order["delivery_fee"] = float(parse_cost.search(cost).group(0))    
    ## total ##
    total = soup.find("p", string = re.compile(r"Total"))
    if total:   # creation of key if html tag is found
        order["order_total_paid"] = float(parse_cost.search(total.find_next("p").text).group(0))
    return order

# function to retrieve all order items' info 
def order_items(soup):
    listitem = soup.find('table', attrs = {"role": "listitem"})
    count = len(list(listitem.contents))//2   # total number of items (row of the table)
    order_items = []   # storing
    thresh = listitem.find('td')  # we sequentially go over the table tags and pick the text of the first paragraph
    for __ in range(count):   # rows of the table
        order_item = dict.fromkeys(keys_items)
        for parse, col in zip([parse_q, parse_t, parse_p], [keys_items[1], keys_items[0], keys_items[2]]):
            order_item[col] = parse.search(thresh.p.get_text(strip = True)).group(0).replace(u'\xa0', u' ')  # we parse all field with appropriate regex, subtitusting the unicode character for the non-breaking space since we are capturing everything
            thresh = thresh.find_next('td')
        order_item["quantity"] = float(order_item["quantity"])  # float conversion of quantity of items
        order_item["name"] = order_item["name"].strip(' ,.-')  # cleaning the name
        order_item["price"] = float(order_item["price"].replace(",", "."))  # float conversion of prices
        order_items.append(order_item)  # appending everything to the store
    return order_items

if __name__ == "__main__":
    compless = []   # outer list of objects
    for file in os.listdir('deliveroo'):
        with open(f"deliveroo/{file}", "r", encoding = "utf-8") as email:
            soup = BeautifulSoup(email, 'lxml') 
            single = dict.fromkeys(keys_fin)   # single item, dictionary with keys [order, restaurant, customer, order_items]
            restaurant_, customer_ = restaurant_and_customer(soup)
            order_ = order(soup, email)
            order_items_ = order_items(soup)
            for key, value in zip(keys_fin, [order_, restaurant_, customer_, order_items_]):
                single[key] = value  # updating the dictionary for the single item
        compless.append(single)  # appending the single item

    with open("nico_final.json", "w", encoding = "utf-8") as f:
        json.dump(compless, f, indent=2, ensure_ascii=False)

executionTime = (time.time() - startTime)
print('Execution time in seconds: ' + str(executionTime))