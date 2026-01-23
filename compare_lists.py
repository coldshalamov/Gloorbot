
import re

def compare_lists():
    # 1. Load User's Current List
    shop_all_urls = set()
    with open('SHOP_ALL_URLS_GENERATED.txt', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                # Normalize: remove query params, lower case, strip
                url = line.strip().split('?')[0].lower()
                shop_all_urls.add(url)

    print(f"Loaded {len(shop_all_urls)} existing Shop All URLs.")

    # 2. Parse User's Sitemap Snippet
    # I will paste the snippet here directly as a string for safety/ease
    sitemap_snippet = """
<url><loc>https://www.lowes.com/pl/accessible-home/4294644799</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bathroom/37721669146437</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bathroom/ada-compliant-toilets/37721669146439</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bathroom/accessible-faucets-shower-heads/37721669146440</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bathroom/accessible-showers-tubs/37721669146438</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bathroom/accessible-vanities/2010022327093</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bathroom/bathroom-aids/37721669146449</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bedroom/4294644781</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bedroom/bed-rails/4294644780</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bedroom/bedside-commodes/4294644777</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-bedroom/overbed-tables/4294644779</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-entry-home/37721669146444</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-entry-home/accessible-door-handles-locks/2111360914830</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-entry-home/non-slip-entry-mats/37721669146448</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-entry-home/touch-lamps-lighting/37721669146447</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-entry-home/wide-entry-doors/37721669146446</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/1111913019980</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-cabinet-hardware/37721669146441</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-cooking/37721669146471</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-cooking/accessible-cooktops/37721669146474</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-cooking/accessible-microwaves/37721669146473</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-cooking/accessible-ovens/37721669146475</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-cooking/accessible-ranges/2920583412062</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-dishwashers/37721669146476</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-kitchen-faucets/2021758280227</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-kitchen-sinks/37721669146433</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-laundry/37721669146472</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/accessible-refrigerators/37721669146477</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/non-slip-kitchen-floor-mats/37721669146443</loc></url>
<url><loc>https://www.lowes.com/pl/accessible-kitchen/pull-out-cabinet-organizers/37721669146442</loc></url>
<url><loc>https://www.lowes.com/pl/daily-assistance/4294644797</loc></url>
<url><loc>https://www.lowes.com/pl/daily-assistance/dressing-aid-kits/4294644795</loc></url>
<url><loc>https://www.lowes.com/pl/daily-assistance/emergency-alert-devices/4294644783</loc></url>
<url><loc>https://www.lowes.com/pl/daily-assistance/shopping-carts/4294644798</loc></url>
<url><loc>https://www.lowes.com/pl/injury-relief-physical-therapy/4294644776</loc></url>
<url><loc>https://www.lowes.com/pl/injury-relief-physical-therapy/orthopedic-pillows-cushions/4294644775</loc></url>
<url><loc>https://www.lowes.com/pl/injury-relief-physical-therapy/physical-therapy-equipment/4294644772</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/4294644793</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/medical-walking-canes/4294644788</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/reaching-tools/4294642674</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/walkers-wheelchairs-rollators/4294644785</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/wheelchair-accessories/4294644789</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/wheelchair-ramps-components/4294642679</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/wheelchair-ramps-components/wheelchair-ramp-components/4294642677</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/wheelchair-ramps-components/wheelchair-ramp-landings-runs/4294642676</loc></url>
<url><loc>https://www.lowes.com/pl/wheelchairs-mobility-aids/wheelchair-ramps-components/wheelchair-ramps/4294642675</loc></url>
<url><loc>https://www.lowes.com/pl/animal-pet-care/4294610578</loc></url>
<url><loc>https://www.lowes.com/pl/livestock-supplies/1697941494</loc></url>
<url><loc>https://www.lowes.com/pl/livestock-supplies/chicken-coops-rabbit-hutches/4294610501</loc></url>
<url><loc>https://www.lowes.com/pl/livestock-supplies/horse-stalls-accessories/2261814275</loc></url>
<url><loc>https://www.lowes.com/pl/livestock-supplies/livestock-feed-supplements/3611853293924</loc></url>
<url><loc>https://www.lowes.com/pl/livestock-supplies/livestock-feeders-accessories/4294610575</loc></url>
<url><loc>https://www.lowes.com/pl/livestock-supplies/poultry-feed/2520347717591</loc></url>
<url><loc>https://www.lowes.com/pl/livestock-supplies/stock-tanks/4294610574</loc></url>
<url><loc>https://www.lowes.com/pl/pet-beds-houses-furniture/2544332199</loc></url>
<url><loc>https://www.lowes.com/pl/pet-beds-houses-furniture/cat-trees-scratchers/4294506791</loc></url>
<url><loc>https://www.lowes.com/pl/pet-beds-houses-furniture/pet-beds/4294610555</loc></url>
<url><loc>https://www.lowes.com/pl/pet-beds-houses-furniture/pet-houses/4294610512</loc></url>
<url><loc>https://www.lowes.com/pl/pet-beds-houses-furniture/pet-steps-ramps/4294610572</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/2318112555</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/cat-litter-concealment/3310177499046</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/cat-litter-concealment/cat-litter/3810937269245</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/cat-litter-concealment/litter-box-concealment/4196495263</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/cat-litter-concealment/litter-boxes/4121196238324</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/dog-cleaning-potty/3120024371076</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/dog-cleaning-potty/deodorizers-stain-removers/4411596860529</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/dog-cleaning-potty/pet-sod-pieces/5121292475944</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/dog-cleaning-potty/poop-scoops-accessories/4521250044138</loc></url>
<url><loc>https://www.lowes.com/pl/pet-cleaning-waste-supplies/dog-cleaning-potty/puppy-training-pads/4520725463353</loc></url>
<url><loc>https://www.lowes.com/pl/pet-clippers-scissors-brushes/3121493845732</loc></url>
<url><loc>https://www.lowes.com/pl/pet-clothing-accessories/2921724317701</loc></url>
<url><loc>https://www.lowes.com/pl/pet-clothing-accessories/pet-accessories/1775183927</loc></url>
<url><loc>https://www.lowes.com/pl/pet-clothing-accessories/pet-clothing/3900884986</loc></url>
<url><loc>https://www.lowes.com/pl/pet-doors-gates/4294610550</loc></url>
<url><loc>https://www.lowes.com/pl/pet-doors-gates/pet-door-accessories/4294610548</loc></url>
<url><loc>https://www.lowes.com/pl/pet-doors-gates/pet-doors/4294610549</loc></url>
<url><loc>https://www.lowes.com/pl/pet-doors-gates/pet-gates/4294610547</loc></url>
<url><loc>https://www.lowes.com/pl/pet-feeding-supplies/2510803352</loc></url>
<url><loc>https://www.lowes.com/pl/pet-feeding-supplies/feeders/2720480537313</loc></url>
<url><loc>https://www.lowes.com/pl/pet-feeding-supplies/food-water-bowls/3211056254101</loc></url>
<url><loc>https://www.lowes.com/pl/pet-feeding-supplies/fountains-waterers/3312081504083</loc></url>
<url><loc>https://www.lowes.com/pl/pet-feeding-supplies/pet-food/2710431208428</loc></url>
<url><loc>https://www.lowes.com/pl/pet-feeding-supplies/placemats/2711196366065</loc></url>
<url><loc>https://www.lowes.com/pl/pet-feeding-supplies/storage-accessories/3520543343864</loc></url>
<url><loc>https://www.lowes.com/pl/pet-fencing-training/3583519698</loc></url>
<url><loc>https://www.lowes.com/pl/pet-fencing-training/barriers-dig-protection/4125235027</loc></url>
<url><loc>https://www.lowes.com/pl/pet-fencing-training/pet-fence-receiver-collars/4294610505</loc></url>
<url><loc>https://www.lowes.com/pl/pet-fencing-training/pet-training-batteries/2522787061</loc></url>
<url><loc>https://www.lowes.com/pl/pet-fencing-training/pet-training-collars/4294610570</loc></url>
<url><loc>https://www.lowes.com/pl/pet-fencing-training/remote-pet-trainers/4294610569</loc></url>
<url><loc>https://www.lowes.com/pl/pet-fencing-training/underground-pet-fences/4294610508</loc></url>
<url><loc>https://www.lowes.com/pl/pet-fencing-training/wireless-pet-fences/4294610504</loc></url>
<url><loc>https://www.lowes.com/pl/pet-grooming-health/4294610546</loc></url>
<url><loc>https://www.lowes.com/pl/pet-grooming-health/pet-grooming-tools/4294610542</loc></url>
<url><loc>https://www.lowes.com/pl/pet-grooming-health/pet-grooming-tools/grooming-supplies-accessories/5210443769222</loc></url>
<url><loc>https://www.lowes.com/pl/pet-grooming-health/pet-grooming-tools/shampoos-conditioners-sprays/4810523462016</loc></url>
<url><loc>https://www.lowes.com/pl/pet-grooming-health/pet-healthcare-treatments/3910792087089</loc></url>
<url><loc>https://www.lowes.com/pl/pet-grooming-health/pet-healthcare-treatments/pet-flea-tick-treatments/1360365504</loc></url>
<url><loc>https://www.lowes.com/pl/pet-kennels-crates/778128516</loc></url>
<url><loc>https://www.lowes.com/pl/pet-kennels-crates/crates-kennels/4294610556</loc></url>
<url><loc>https://www.lowes.com/pl/pet-kennels-crates/dog-pens-runs/4294610510</loc></url>
<url><loc>https://www.lowes.com/pl/pet-kennels-crates/pet-kennel-crate-accessories/2125303942</loc></url>
<url><loc>https://www.lowes.com/pl/pet-leashes-collars-harnesses/4233103602</loc></url>
<url><loc>https://www.lowes.com/pl/pet-leashes-collars-harnesses/pet-collars-harnesses/1579663759</loc></url>
<url><loc>https://www.lowes.com/pl/pet-leashes-collars-harnesses/pet-leashes/4294610534</loc></url>
<url><loc>https://www.lowes.com/pl/pet-toys-treats/4294610530</loc></url>
<url><loc>https://www.lowes.com/pl/pet-toys-treats/pet-toys/2459556657</loc></url>
<url><loc>https://www.lowes.com/pl/pet-toys-treats/pet-treats/1943201441</loc></url>
<url><loc>https://www.lowes.com/pl/pet-travel-transportation/2620088367057</loc></url>
<url><loc>https://www.lowes.com/pl/pet-travel-transportation/pet-car-seats-covers/3840252608</loc></url>
<url><loc>https://www.lowes.com/pl/pet-travel-transportation/pet-carriers/15211541027986</loc></url>
<url><loc>https://www.lowes.com/pl/pet-travel-transportation/pet-strollers-bicycle-trailers/15211541027987</loc></url>
<url><loc>https://www.lowes.com/pl/pet-travel-transportation/pet-travel-accessories/4220738090549</loc></url>
<url><loc>https://www.lowes.com/pl/pet-vitamins-supplements/2620555201638</loc></url>
<url><loc>https://www.lowes.com/pl/terrariums-habitats/2311219941942</loc></url>"""

    # Extract URLs from XML style
    sitemap_matches = re.findall(r'<loc>(.*?)</loc>', sitemap_snippet)
    sitemap_urls = set(u.strip().lower() for u in sitemap_matches)
    
    print(f"Extracted {len(sitemap_urls)} URLs from snippet.")
    
    # 3. Check for specific exclusions
    missing = []
    
    for sm_url in sitemap_urls:
        if "lowesbrands" in sm_url or "departments" in sm_url or "lowes.com" == sm_url: continue
        
        # Exact match check
        if sm_url not in shop_all_urls:
            missing.append(sm_url)
            
    print(f"\nMissing Coverage ({len(missing)} URLs):")
    if not missing:
        print("GOOD NEWS: All snippet URLs are present in your SHOP_ALL_URLS list.")
    else:
        for m in sorted(missing):
            print(f"FAILED TO FIND: {m}")
            
    # Also check if we have them but with different IDs? 
    # That would imply the IDs in your file are different or my parsing is strict.

    # Let's count how many "pet" related things are in both lists
    user_pet = [u for u in shop_all_urls if 'pet-' in u or 'animal' in u]
    print(f"\nPet categories in your list: {len(user_pet)}")
    
if __name__ == "__main__":
    compare_lists()
