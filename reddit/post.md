## Title

[OC] The middle of nowhere: I measured how far every point on land is from the nearest town. A quarter of the land outside Antarctica is more than 100 km from a place of 1,000 people

## Body

I measured the straight-line distance from every point on land (a 0.1° grid, 2,147,063 cells) to the nearest of 171,737 places with 1,000+ people in the GeoNames gazetteer, and to the nearest city and coast. 25% of the land outside Antarctica is more than 100 km from a town, but only 1.3% is more than 500 km away. The most remote mainland spots: Cape Chelyuskin in Siberia (641 km), the Great Victoria Desert in Australia (579 km) and the Libyan Desert of Sudan (517 km). Counting islands, Marion Island in the Southern Ocean is 1,749 km from a town. The famous pole of inaccessibility in China, the land farthest from the sea, is just 65 km from one. In Britain the most remote spot is near Cape Wrath, 82 km from Ullapool; England's is Kielder Forest, whose nearest town is in Scotland. Caveats: villages under 1,000 people are not counted, and Antarctica's research stations are not towns. Interactive map where you can pick any country or click anywhere: https://maps.tristanhotham.com/remote-places/

## Source comment

Source: GeoNames cities1000 (geonames.org, CC BY 4.0, via lutangar/cities.json) for towns; Natural Earth for cities of 100,000+ and 1,000,000+, land, coast and countries. Great-circle distances on a 0.1° area-weighted grid with a k-d tree; maxima refined to 0.01°.

Tools: Python (numpy, scipy, shapely, pyproj, matplotlib); MapLibre for the interactive map.

Interactive version: https://maps.tristanhotham.com/remote-places/
Paper: https://doi.org/10.5281/zenodo.23873015
Blog post: https://blog.tristanhotham.com/2026/10/31/remote-places/
