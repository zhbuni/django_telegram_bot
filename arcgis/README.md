# Arcgis - free reverse geocodinglocation = models.OneToOneField(Location, on_delete=models.CASCADE, primary_key=True)


This package is optional.

If a Telegram user sends you his/her location, you may want to have more information than just coordinates (lat, lng). Arcgis is a free reverse geocoder which can give you more details about a location: City, Country, Region, ... Read `models.py` for more information.