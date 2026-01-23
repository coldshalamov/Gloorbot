
import re

def test_leaf_logic():
    # The user's "nightmare" list
    urls = [
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/4294612714-87589463",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/4294612701",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/attachment-cultivators/4294542197",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/attachment-snow-blowers/4294414331",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/attachment-tank-sprayers/4294612696",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/box-scrapers/4294542199",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/dethatchers/4294612693",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/disc-harrows/4294542198",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/dump-carts/4294612692",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/lawn-rollers/4294612700",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/lawn-sweepers/4294612691",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/lawn-vacuums/4294612690",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/mulching-kits/4294612689",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/riding-lawn-mower-canopies/4294612695",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/trail-cutters/4294612698",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-attachments/trail-mowers/4294612697",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-parts-accessories/4294612713",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-parts-accessories/lawn-mower-belts/4294612708",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-parts-accessories/lawn-mower-blades/4294612712",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-parts-accessories/lawn-mower-parts/4294542196",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-parts-accessories/riding-lawn-mower-accessories/4294612709",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/lawn-mower-parts-accessories/robotic-lawn-mower-parts-accessories/6211139717570",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/push-lawn-mowers/4294612707",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/push-lawn-mowers/corded-electric-push-lawn-mowers/4294612705",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/push-lawn-mowers/cordless-electric-push-lawn-mowers/4294612706",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/push-lawn-mowers/gas-push-lawn-mowers/4294612703",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/push-lawn-mowers/reel-lawn-mowers/4294612704",
        "https://www.lowes.com/pl/outdoor-tools-equipment/lawn-mowers/robotic-lawn-mowers/4294612702-342505339"
    ]

    def get_concept(u):
        if 'lowes.com' in u:
            path = u.split('lowes.com')[1]
        else:
            path = u
        return re.sub(r'/\d+[-]?.*$', '', path)

    url_data = []
    for u in urls:
        c = get_concept(u)
        url_data.append({'url': u, 'concept': c, 'order_len': len(c)})
    
    # Sort for display only
    # To detect redundancy, we iterate parents vs children.
    
    to_remove = set()
    debug_map = {} # parent -> list of kids
    
    for i in range(len(url_data)):
        parent = url_data[i]
        
        for j in range(len(url_data)):
            if i == j: continue
            child = url_data[j]
            
            # Check if parent is prefix of child
            if child['concept'].startswith(parent['concept'] + '/'):
                to_remove.add(parent['url'])
                debug_map.setdefault(parent['concept'], []).append(child['concept'].replace(parent['concept'], '...'))
                break 
    
    print(f"Total Input: {len(urls)}")
    print(f"Identified Parents to Prune: {len(to_remove)}")
    print("\n[Pruned Parents] -> [Because they contain...]")
    for p, kids in debug_map.items():
        print(f"  {p}")
        print(f"    -> {kids[0]}")
        
    print("\n[Kept URLs (Leaf Nodes)]")
    kept = [u for u in urls if u not in to_remove]
    kept.sort()
    for u in kept:
        print(f"  {u.split('/pl/')[-1]}")

if __name__ == "__main__":
    test_leaf_logic()
