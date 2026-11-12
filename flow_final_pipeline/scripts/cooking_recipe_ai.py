# -*- coding: utf-8 -*-
"""Auto-generate POV cooking recipes, 6-panel macro actions, and 3-beat Vietnamese voiceovers for Template 005."""
import json
import re
import socket
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SUGGESTED_DISHES = [
    "Thịt kho tàu trứng cút",
    "Sườn xào chua ngọt",
    "Cánh gà chiên nước mắm",
    "Lẩu Thái tôm nấm",
    "Bò lúc lắc khoai tây",
    "Tôm sốt bơ tỏi",
    "Phở bò tái nạm",
    "Canh chua cá lóc",
    "Mì cay hải sản",
    "Cơm chiên hải sản",
    "Chân gà sả tắc",
    "Trà đào cam sả",
]

BASE_KITCHEN_CONTINUITY = (
    "Bright clean white home kitchen, soft natural window light from camera left. "
    "Neutral ivory highlights, gently warm midtones, clean whites without an overall yellow cast. "
    "Only a narrow softly blurred background strip with pale wood utensils. Same slender adult hands, natural short nails, "
    "no jewelry; clear glass prep bowls, wooden spatula and wooden chopsticks. Only one active hand and "
    "one utensil at a time; chopsticks are exactly one pair held together by one hand, never two opposing pairs. "
    "No face or presenter. Photorealistic food-commercial 85-100mm macro lens look, readable contact point, "
    "realistic wet textures and restrained glossy highlights. "
)


def _strip_accents(text: str) -> str:
    s = str(text or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def _trim_vn_words(line: str, max_words: int = 12) -> str:
    """Ensure a Vietnamese narration phrase stays concise and readable within a 2.6s beat."""
    replacements = {
        "1": "một", "2": "hai", "3": "ba", "4": "bốn", "5": "năm",
        "6": "sáu", "7": "bảy", "8": "tám", "9": "chín", "10": "mười",
        "15": "mười lăm", "20": "hai mươi", "30": "ba mươi",
    }
    tokens = []
    for raw in str(line or "").replace("—", " ").replace("–", " ").split():
        clean = raw.strip()
        bare = clean.strip(",.;:!?\"'()")
        if bare in replacements:
            suffix = clean[len(bare):]
            clean = replacements[bare] + suffix
        if clean:
            tokens.append(clean)
    if len(tokens) > max_words:
        tokens = tokens[:max_words]
        tokens[-1] = tokens[-1].rstrip(",;:")
        if tokens[-1] and tokens[-1][-1] not in ".!?":
            tokens[-1] += "."
    return " ".join(tokens)


def _dialect_tail(region: str, kind: str = "invite") -> str:
    reg = str(region or "north").lower()
    if kind == "open":
        if reg == "south":
            return "thơm nức mũi nè"
        if reg == "central":
            return "đậm đà thơm lừng"
        return "thơm lừng gian bếp"
    if kind == "mid":
        if reg == "south":
            return "thấm vị ngon mê ly nha"
        if reg == "central":
            return "thấm đều đậm vị quê nhà"
        return "thấm đều đậm đà từng miếng"
    if reg == "south":
        return "ăn cơm nóng cuốn xỉu nha"
    if reg == "central":
        return "mời cả nhà thưởng thức nhé"
    return "ăn cùng cơm nóng chuẩn vị"


# ---------------------------------------------------------------------------
# Curated high-precision culinary blueprints for flagship Vietnamese dishes
# ---------------------------------------------------------------------------

def _curated_blueprints(region: str):
    open_phrase = _dialect_tail(region, "open")
    invite_phrase = _dialect_tail(region, "invite")
    return {
        "lau thai": {
            "dish_default": "Lẩu Thái tôm nấm",
            "dish_en": "Thai-style shrimp and mushroom hotpot",
            "visual_continuity": (
                "The same matte warm-ivory pot with pale interior. "
                + BASE_KITCHEN_CONTINUITY
                + "Once seasoning is added: rich orange-red broth, distinct red oil ribbons, clear bubbling detail; "
                "fresh red tomatoes, yellow corn, green leaves and pink-orange cooked shrimp. "
                "Do not color the unseasoned broth red or add ingredients before their specified step."
            ),
            "clips": [
                {
                    "title": "Phi thơm và nấu nền",
                    "start_state": "Empty clean pot; all ingredients still separate.",
                    "actions": [
                        "Tilt a small clear glass bowl and pour one continuous thin golden oil stream into the empty ivory pot; oil spreads into a reflective film.",
                        "Tilt a clear glass bowl to drop thin crushed lemongrass into the established oil; show pieces mid-fall and tiny bubbles at contact.",
                        "Tilt a clear glass bowl so purple-white shallot slices tumble onto the established lemongrass; translucent layers catch the light.",
                        "Stir the lemongrass and shallots once with the wooden spatula; aromatics glisten without burning.",
                        "Tip glossy ripe red tomato wedges from a clear glass bowl into the established aromatics; first wedges land while others fall; no seafood or mushrooms yet.",
                        "Pour clear broth into the tomatoes and aromatics; end with the pot half full and light steam.",
                    ],
                    "actions_vn": [
                        "Rót dòng dầu vàng óng vào nồi men ngà sạch",
                        "Thả sả đập dập vào lớp dầu nóng sủi tăm nhẹ",
                        "Cho hành tím thái lát vào phi cùng sả",
                        "Đảo nhẹ sả và hành tím bằng muôi gỗ cho dậy mùi",
                        "Thả cà chua bổ múi cau đỏ mọng vào nồi nền thơm",
                        "Châm nước dùng trong vắt ngập nửa nồi bốc khói nhẹ",
                    ],
                    "voiceover": [
                        _trim_vn_words(f"Nấu nồi lẩu Thái chua cay {open_phrase}."),
                        "Phi thơm sả đập dập cùng hành tím thái lát.",
                        "Thêm cà chua tươi rồi châm nước dùng ngọt thanh.",
                    ],
                },
                {
                    "title": "Tạo vị nước lẩu và cho rau nấm",
                    "start_state": "Pot half full of broth with lemongrass, shallots and tomato wedges from clip 1; no seafood yet.",
                    "actions": [
                        "Stir one spoonful of red Thai chili paste into the existing broth; broth becomes orange-red.",
                        "Drop two torn kaffir lime leaves into the orange-red broth; keep existing tomato and aromatics.",
                        "Add thin pale galangal slices to the broth; slices land on the visible surface.",
                        "Show the same seasoned broth gently simmering, small bubbles and wisps of steam; no hand action.",
                        "Tip a small cluster of oyster mushrooms from a clear glass bowl into the simmering orange-red broth; visible landing ripples.",
                        "Tip three yellow corn rounds from a clear glass bowl into the same pot; natural falling arc and small splash, mushrooms remain visible.",
                    ],
                    "actions_vn": [
                        "Khuấy sốt lẩu Thái cho nước dùng lên màu đỏ cam",
                        "Thả lá chanh vò nhẹ vào mặt nước lẩu đang ấm",
                        "Thêm những lát riềng tươi dậy tầng hương đặc trưng",
                        "Nước lẩu sôi lăn tăn nổi vân dầu đỏ cam đẹp mắt",
                        "Thả cụm nấm bào ngư trắng tươi vào nồi nước sôi",
                        "Cho tiếp khoanh bắp mỹ vàng ươm ngọt nước",
                    ],
                    "voiceover": [
                        "Hòa sốt lẩu Thái cho màu đỏ cam sóng sánh.",
                        "Thả lá chanh và riềng tươi dậy hương đặc trưng.",
                        "Nước sôi đều thì cho nấm tươi và bắp ngọt.",
                    ],
                },
                {
                    "title": "Nấu tôm và hoàn thiện",
                    "start_state": "Simmering orange-red broth with tomatoes, aromatics, lime leaves, mushrooms and corn from clip 2.",
                    "actions": [
                        "Lower peeled raw shrimp one by one into the simmering broth with wooden cooking chopsticks.",
                        "Show a later cooking moment: the same shrimp now opaque pink and curled in gently bubbling broth; no raw shrimp remain.",
                        "Add a small handful of clean fresh bok choy leaves to the shrimp and mushrooms in the pot.",
                        "Gently press the green leaves into the hot broth with the same wooden spatula; leaves soften but stay green.",
                        "Show the finished hotpot surface in close macro: glossy cooked pink shrimp, mushrooms, yellow corn and green leaves in rich orange-red broth with distinct oil ribbons and gentle bubbling.",
                        "Hero shot: wooden chopsticks slowly lift one cooked pink-orange shrimp and a mushroom above the SAME finished pot toward the lens; broth droplets fall back, keep the food in focus and the pot softly behind. No serving bowl.",
                    ],
                    "actions_vn": [
                        "Dùng đũa gỗ thả từng con tôm tươi vào nước lẩu sôi",
                        "Tôm chín chuyển màu hồng cam cong tròn săn chắc",
                        "Thả nắm cải thìa xanh mướt vào nồi tôm nấm",
                        "Nhấn nhẹ rau xanh ngập vào nước lẩu nóng hổi",
                        "Cận cảnh mặt nồi lẩu hoàn chỉnh sôi nhẹ hấp dẫn",
                        "Đũa gỗ gắp con tôm hồng cam và nấm đưa gần ống kính",
                    ],
                    "voiceover": [
                        "Thả tôm tươi vào nước sôi cho chín hồng giòn ngọt.",
                        "Nhúng thêm rau cải xanh mướt giữ trọn độ tươi.",
                        _trim_vn_words(f"Nồi lẩu nóng hổi đậm vị, mời cả nhà thưởng thức."),
                    ],
                },
            ],
        },
        "thit kho": {
            "dish_default": "Thịt kho tàu trứng cút",
            "dish_en": "Vietnamese caramelized braised pork belly with quail eggs",
            "visual_continuity": (
                "The same matte warm-ivory heavy braising pot with pale interior. "
                + BASE_KITCHEN_CONTINUITY
                + "Progressive caramel braising color: clear golden caramel base deepening into rich glossy amber-brown sauce "
                "coating thick-cut marbled pork belly cubes and smooth peeled quail eggs. Never add shrimp, corn or green vegetables inside the pot."
            ),
            "clips": [
                {
                    "title": "Thắng nước màu và áp chảo thịt",
                    "start_state": "Empty clean warm-ivory braising pot; raw pork belly cubes, aromatics and peeled quail eggs separate.",
                    "actions": [
                        "Tilt a small clear glass bowl to pour a thin stream of oil and golden sugar syrup into the warm ivory pot; gentle amber bubbles form.",
                        "Stir the melting caramel once with a wooden spatula until it turns glossy honey-amber without burning.",
                        "Drop minced shallots and garlic from a clear glass bowl into the warm amber base; fragrant tiny bubbles surround the aromatics.",
                        "Tip thick-cut marbled pork belly cubes from a glass bowl into the pot; cubes land cleanly in the glossy amber aromatics.",
                        "Stir and turn the pork belly cubes with the wooden spatula so the outer surfaces firm up with a light golden caramel coat.",
                        "Pour golden savory fish sauce from a small glass spout bowl over the seared pork; steam rises with glossy caramel highlights.",
                    ],
                    "actions_vn": [
                        "Rót dầu và đường thắng lên màu mật ong óng ả",
                        "Khuấy nhẹ bằng muôi gỗ cho nước hàng chuyển màu hổ phách",
                        "Phi thơm hành tím và tỏi băm sủi tăm dậy mùi",
                        "Cho thịt ba chỉ thái vuông dày vào đảo săn",
                        "Đảo đều để từng miếng thịt áo lớp màu vàng nâu đẹp mắt",
                        "Rưới nước mắm ngon cho thịt dậy hương đậm đà",
                    ],
                    "voiceover": [
                        _trim_vn_words(f"Mẻ thịt kho tàu lên màu cánh gián {open_phrase}."),
                        "Thắng nước hàng mật ong rồi phi thơm hành tỏi.",
                        "Đảo săn thịt ba chỉ cùng chén nước mắm ngon.",
                    ],
                },
                {
                    "title": "Kho nước dừa tươi và cho trứng",
                    "start_state": "Pot holds caramel-coated seared pork belly cubes with shallots, garlic and fish sauce glaze; no eggs yet.",
                    "actions": [
                        "Pour clear fresh coconut water in a steady stream into the pot until it just covers the caramel-coated pork belly cubes.",
                        "Drop two whole red chili peppers into the simmering amber coconut braising liquid; gentle ripples spread.",
                        "Show a close macro of the amber braising broth gently simmering with fine glossy fat droplets and translucent steam.",
                        "Tilt a clear glass bowl to gently roll peeled smooth white quail eggs into the simmering amber pork pot.",
                        "Sweep the wooden spatula gently once so the white quail eggs submerge and take on a light golden-amber tint.",
                        "Show a later slow-braised moment: broth reduced halfway into a richer mahogany-amber glaze coating tender pork and golden eggs.",
                    ],
                    "actions_vn": [
                        "Châm nước dừa tươi ngập xăm xắp mặt thịt ba chỉ",
                        "Thả hai trái ớt đỏ nguyên trái tạo vị the dịu",
                        "Nồi thịt sôi liu riu ánh lên lớp nước màu trong veo",
                        "Cho trứng cút bóc vỏ trắng mịn vào kho cùng thịt",
                        "Đảo nhẹ cho trứng thấm đều màu hổ phách óng mượt",
                        "Nước kho sánh lại ôm trọn miếng thịt mềm rục",
                    ],
                    "voiceover": [
                        "Châm nước dừa tươi ngập thịt cho vị ngọt tự nhiên.",
                        "Kho lửa nhỏ liu riu rồi thả trứng cút trắng mịn.",
                        "Nước sốt keo dần thấm đẫm màu nâu hổ phách.",
                    ],
                },
                {
                    "title": "Sánh sốt hổ phách và gắp thành phẩm",
                    "start_state": "Rich glossy amber-brown reduced coconut glaze simmering gently around tender pork belly cubes and golden-braised quail eggs.",
                    "actions": [
                        "Show close surface macro of the thick glossy amber-brown caramel sauce bubbling slowly around translucent pork belly layers.",
                        "Sprinkle cracked black pepper from above onto the glossy braised pork belly and golden quail eggs.",
                        "Scatter finely sliced green scallion rings lightly across the glossy amber pork surface for fresh contrast.",
                        "Gently baste glossy amber sauce over a tender pork belly cube using the wooden spoon; rich sheen catches window light.",
                        "Show close macro of the finished pot: glistening tender marbled pork belly, amber eggs, red chili and green scallions.",
                        "Hero shot: wooden chopsticks slowly lift one trembling tender caramelized pork belly cube above the SAME pot toward the lens; amber glaze drips back. No serving bowl.",
                    ],
                    "actions_vn": [
                        "Cận cảnh nước kho kẹo sánh sôi nhẹ quanh miếng ba chỉ",
                        "Rắc tiêu đen xay thơm nồng lên mặt nồi thịt nóng",
                        "Điểm chút hành lá cắt nhỏ xanh tươi bắt mắt",
                        "Rưới muỗng sốt nâu óng lên từng thớ thịt mềm",
                        "Nồi thịt kho hoàn thiện bóng mượt thơm nức mũi",
                        "Đũa gỗ gắp miếng ba chỉ mềm tan đưa sát ống kính",
                    ],
                    "voiceover": [
                        "Thịt chín mềm trong veo, rắc thêm chút tiêu xay thơm.",
                        "Sốt kho sánh bóng quyện đều từng miếng thịt trứng.",
                        _trim_vn_words(f"Gắp miếng ba chỉ mềm tan, {invite_phrase}."),
                    ],
                },
            ],
        },
        "suon xao chua ngot": {
            "dish_default": "Sườn xào chua ngọt",
            "dish_en": "Vietnamese sweet and sour glazed pork ribs",
            "visual_continuity": (
                "The same wide matte warm-ivory deep skillet with pale interior. "
                + BASE_KITCHEN_CONTINUITY
                + "Pork short ribs progress from golden-seared edges to a rich glossy ruby-amber sweet-and-sour glaze "
                "with crisp red-and-yellow bell peppers and shallots. No broth soup, no shrimp, no noodles."
            ),
            "clips": [
                {
                    "title": "Áp chảo sườn non vàng cạnh",
                    "start_state": "Clean warm-ivory deep skillet; blanched pat-dried pork short ribs and aromatics prepared in glass bowls.",
                    "actions": [
                        "Tilt a clear glass bowl to pour a thin ribbon of golden cooking oil into the warm ivory skillet; oil shimmers.",
                        "Place meaty pork short ribs into the hot oil with wooden chopsticks; gentle golden sizzle around each rib.",
                        "Turn the pork ribs with wooden chopsticks to reveal evenly browned caramelized golden edges on both sides.",
                        "Tip minced garlic and sliced shallots from a clear glass bowl onto the golden ribs; fragrant bubbles form immediately.",
                        "Toss and stir the ribs with the wooden spatula so garlic and shallots turn lightly golden without burning.",
                        "Show close macro of sizzling golden-browned pork ribs glistening with aromatic garlic oil in the skillet.",
                    ],
                    "actions_vn": [
                        "Rót làn dầu vàng mỏng vào chảo sâu lòng nóng",
                        "Đặt từng miếng sườn non vào áp chảo xèo xèo",
                        "Trở đều mặt sườn bằng đũa gỗ cho xém vàng hai cạnh",
                        "Cho tỏi băm và hành tím vào phi thơm cùng sườn",
                        "Đảo đều tay để hương hành tỏi quyện quanh miếng sườn",
                        "Cận cảnh sườn non vàng ươm bóng dầu thơm nức",
                    ],
                    "voiceover": [
                        _trim_vn_words(f"Sườn xào chua ngọt bóng mượt {open_phrase}."),
                        "Áp chảo sườn non cho xém vàng đều hai mặt.",
                        "Phi thơm hành tỏi băm dậy mùi hấp dẫn ngay.",
                    ],
                },
                {
                    "title": "Xào ớt chuông và rưới sốt chua ngọt",
                    "start_state": "Golden-browned pork short ribs with fragrant garlic and shallots in the warm ivory skillet.",
                    "actions": [
                        "Tip crisp red and yellow bell pepper chunks and onion wedges from a glass bowl into the skillet with the golden ribs.",
                        "Stir-fry once with the wooden spatula so the colorful peppers brighten with a light glossy oil sheen.",
                        "Pour a pre-mixed ruby-orange sweet-and-sour tamarind tomato sauce stream from a glass bowl over the sizzling ribs.",
                        "Show immediate bubbling as the tangy-sweet sauce hits the hot skillet and surrounds the ribs and peppers.",
                        "Sweep the wooden spatula through the skillet to coat every pork rib and pepper piece in the vibrant orange-red sauce.",
                        "Show the sauce gently simmering and thickening around the ribs with glossy translucent bubbles.",
                    ],
                    "actions_vn": [
                        "Thêm ớt chuông đỏ vàng và hành tây vào chảo sườn",
                        "Đảo nhanh tay giữ trọn độ giòn ngọt tự nhiên",
                        "Rưới chén nước sốt chua ngọt sóng sánh vào chảo nóng",
                        "Sốt sôi bùng lên bọt mịn thơm lừng cả gian bếp",
                        "Đảo đều cho sốt đỏ cam bám quanh từng dẻ sườn",
                        "Đun lửa vừa cho sốt sệt lại thấm sâu vào thịt",
                    ],
                    "voiceover": [
                        "Thêm ớt chuông giòn ngọt tạo sắc màu tươi tắn.",
                        "Rưới đều chén sốt chua ngọt pha chuẩn tỉ lệ.",
                        "Đảo lửa vừa cho nước sốt sánh lại thấm vị.",
                    ],
                },
                {
                    "title": "Áo sốt bóng mượt và gắp sườn nóng",
                    "start_state": "Thickening ruby-amber sweet-and-sour glaze coating tender pork ribs and colorful bell peppers in the same skillet.",
                    "actions": [
                        "Show close macro of the glossy ruby-amber glaze thickening into shiny ribbons clinging tightly to the ribs.",
                        "Fold the glazed pork ribs once with the wooden spatula; sticky glaze stretches slightly and coats every surface.",
                        "Sprinkle finely chopped green scallions and toasted white sesame seeds lightly over the glossy ribs.",
                        "Show close macro of the finished skillet: caramelized sweet-and-sour ribs, crisp glossy peppers and sesame.",
                        "Grip one plump glazed pork short rib cleanly with wooden chopsticks inside the skillet.",
                        "Hero shot: wooden chopsticks lift the glossy ruby-glazed pork rib above the SAME skillet toward the lens; sticky sauce gleams. No serving plate.",
                    ],
                    "actions_vn": [
                        "Nước sốt keo sánh bóng loáng bám chặt dẻ sườn",
                        "Đảo nhẹ lần cuối cho lớp sốt áo đều óng ả",
                        "Rắc thêm hành lá xanh và mè trắng rang thơm",
                        "Chảo sườn hoàn thiện lên màu đỏ hổ phách bắt mắt",
                        "Đũa gỗ gắp dẻ sườn đầy đặn ngập sốt sánh mịn",
                        "Nâng miếng sườn bóng mượt nóng hổi sát ống kính",
                    ],
                    "voiceover": [
                        "Sốt keo bóng loáng ôm trọn từng dẻ sườn mềm.",
                        "Rắc chút mè rang và hành lá dậy hương thơm.",
                        _trim_vn_words(f"Sườn chua ngọt đậm đà, {invite_phrase}."),
                    ],
                },
            ],
        },
        "ga chien nuoc mam": {
            "dish_default": "Cánh gà chiên nước mắm",
            "dish_en": "Crispy golden chicken wings glazed in Vietnamese garlic fish sauce",
            "visual_continuity": (
                "The same matte warm-ivory deep frying and glazing skillet. "
                + BASE_KITCHEN_CONTINUITY
                + "Chicken wings progress from raw seasoned skin to crisp golden-fried crust, then coated in a sticky amber "
                "garlic-chili fish-sauce glaze. No soup broth, no shrimp."
            ),
            "clips": [
                {
                    "title": "Chiên cánh gà vàng giòn rụm",
                    "start_state": "Clean warm-ivory deep skillet; seasoned pat-dried chicken wings ready in a glass bowl.",
                    "actions": [
                        "Pour clear golden cooking oil from a glass pitcher into the ivory skillet until a shallow frying layer shimmers.",
                        "Lower plump chicken wings one by one into the hot oil with wooden chopsticks; lively crisp bubbles surround the skin.",
                        "Show close macro of chicken wings frying steadily as pale skin tightens and turns light golden.",
                        "Flip a sizzling chicken wing with wooden chopsticks to reveal a blistered crispy golden-brown underside.",
                        "Show all chicken wings evenly crisp and deep golden amidst fine clear frying bubbles.",
                        "Lift a crispy golden chicken wing with wooden chopsticks letting excess clear oil drip back into the skillet.",
                    ],
                    "actions_vn": [
                        "Rót dầu vàng trong veo vào lòng chảo nóng già",
                        "Thả từng chiếc cánh gà vào dầu sôi xèo xèo",
                        "Lớp da gà căng phồng chuyển dần sang sắc vàng ươm",
                        "Trở mặt cánh gà lộ lớp vỏ giòn rụm hấp dẫn",
                        "Cánh gà chín vàng đều nổ bọt dầu giòn tan",
                        "Gắp cánh gà vàng óng để ráo bớt dầu thừa",
                    ],
                    "voiceover": [
                        _trim_vn_words(f"Cánh gà chiên nước mắm giòn rụm {open_phrase}."),
                        "Chiên cánh gà ngập dầu nóng cho da phồng giòn.",
                        "Trở đều hai mặt đến khi vàng ruộm bắt mắt.",
                    ],
                },
                {
                    "title": "Phi tỏi ớt và thắng sốt mắm đường",
                    "start_state": "Skillet drained to a thin aromatic oil film; crispy golden chicken wings resting nearby, minced garlic, chili and fish sauce ready.",
                    "actions": [
                        "Tip generous minced garlic and diced red chili from a glass bowl into the thin hot oil film in the same skillet.",
                        "Stir the garlic and red chili with a wooden spatula until golden, crisp-edged and fragrant.",
                        "Pour golden fish sauce and dissolved palm sugar from a small glass bowl into the sizzling garlic-chili oil.",
                        "Show close macro of the amber garlic-chili fish sauce bubbling into a glossy syrupy glaze.",
                        "Return the crispy golden chicken wings from a bowl directly into the bubbling amber garlic glaze.",
                        "Toss the crispy wings once with the wooden spatula so glossy amber sauce and golden garlic cling to the crust.",
                    ],
                    "actions_vn": [
                        "Cho tỏi băm và ớt đỏ vào phi trong làn dầu mỏng",
                        "Đảo nhanh cho tỏi dậy mùi thơm và vàng giòn",
                        "Rưới hỗn hợp nước mắm đường pha chuẩn vào chảo nóng",
                        "Sốt mắm tỏi sủi bọt keo lại màu hổ phách óng ánh",
                        "Trút phần cánh gà chiên giòn vào chảo sốt đang sôi",
                        "Đảo đều cho sốt mắm tỏi bám quanh lớp vỏ giòn",
                    ],
                    "voiceover": [
                        "Phi vàng tỏi ớt băm cho dậy mùi thơm nồng.",
                        "Pha nước mắm đường đun sôi đến khi sánh keo.",
                        "Cho cánh gà giòn vào đảo nhanh áo đều sốt.",
                    ],
                },
                {
                    "title": "Áo sốt tỏi giòn và gắp cận cảnh",
                    "start_state": "Crispy golden chicken wings coated in bubbling sticky amber garlic-chili fish-sauce glaze inside the ivory skillet.",
                    "actions": [
                        "Turn each glazed chicken wing with wooden chopsticks so every crease gleams with amber garlic-chili glaze.",
                        "Sprinkle crispy fried garlic flakes and thin scallion curls over the glossy wings.",
                        "Show close macro of sticky caramel-amber bubbles clinging to the crackling chicken skin without making it soggy.",
                        "Show the finished skillet of glossy amber-glazed chicken wings topped with golden garlic bits and red chili.",
                        "Grip one plump glossy garlic-glazed chicken wing firmly with wooden chopsticks.",
                        "Hero shot: wooden chopsticks lift the glistening crispy chicken wing above the SAME skillet toward the lens; sticky amber glaze shines. No serving plate.",
                    ],
                    "actions_vn": [
                        "Lật nhẹ từng cánh gà để lớp sốt phủ bóng đều",
                        "Rắc thêm tỏi phi vàng giòn và hành lá thái nhỏ",
                        "Lớp vỏ vẫn giòn tan quyện sốt mắm mặn ngọt",
                        "Cận cảnh chảo cánh gà bóng lưỡng điểm sắc ớt đỏ",
                        "Đũa gỗ gắp chiếc cánh gà đẫm sốt tỏi thơm lừng",
                        "Đưa cánh gà vàng óng giòn rụm lại sát ống kính",
                    ],
                    "voiceover": [
                        "Vỏ ngoài giòn rụm thấm đẫm sốt mắm tỏi kẹo.",
                        "Thêm tỏi phi vàng ươm thơm ngon khó cưỡng.",
                        _trim_vn_words(f"Gắp chiếc cánh gà nóng giòn, {invite_phrase}."),
                    ],
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# General Culinary Synthesis Engine for ANY Vietnamese / International Dish
# ---------------------------------------------------------------------------

INGREDIENT_MAP = [
    (("ba chi", "ba roi", "thit heo", "thit lon"), "thick-cut marbled pork belly pieces", "tender glossy cooked pork belly"),
    (("suon",), "meaty bite-sized pork short ribs", "golden tender glazed pork ribs"),
    (("canh ga",), "plump fresh chicken wings", "crispy golden glazed chicken wings"),
    (("dui ga", "ga "), "bite-sized fresh chicken pieces", "juicy golden cooked chicken pieces"),
    (("bo luc lac", "than bo", "bit tet"), "thick tenderloin beef cubes", "seared caramelized juicy beef cubes"),
    (("bo ", "thit bo", "bap bo"), "thinly sliced ruby-red fresh beef", "tender seared juicy beef slices"),
    (("tom",), "peeled plump fresh shrimp", "glossy pink-orange curled cooked shrimp"),
    (("ca hoi",), "fresh orange-pink salmon fillets", "flaky golden-seared cooked salmon"),
    (("ca ", "ca loc", "ca basa", "ca dieu hong", "ca thu"), "firm fresh fish steaks", "tender flaky cooked fish in savory sauce"),
    (("muc", "bach tuoc"), "scored snowy-white fresh squid", "tender curled glossy cooked squid"),
    (("oc ", "ngheu", "ngao", "hai san"), "clean fresh assorted seafood", "plump glossy cooked seafood"),
    (("ech",), "clean plump frog meat pieces", "golden savory glazed frog meat"),
    (("chan ga",), "crisp blanched white chicken feet", "glossy spicy-tangy coated chicken feet"),
    (("dau hu", "dau phu"), "golden-fried tofu cubes", "puffed golden tofu soaked in savory sauce"),
    (("trung cut",), "peeled smooth white quail eggs", "golden braised quail eggs"),
    (("trung",), "fresh golden farm eggs", "fluffy golden cooked egg"),
    (("nam",), "fresh tender mushroom clusters", "juicy cooked mushrooms"),
    (("mi y", "spaghetti"), "al dente golden spaghetti strands", "glossy sauce-coated spaghetti"),
    (("mi ", "mien", "pho", "bun", "hu tieu"), "fresh tender rice noodles", "glossy savory noodles in rich broth"),
    (("com",), "fluffy steamed white jasmine rice", "golden fragrant wok-tossed fried rice"),
]

VEG_AROMATIC_MAP = [
    (("sa ", "sa tac", "cam sa"), "thinly crushed fresh lemongrass"),
    (("toi",), "finely minced golden garlic"),
    (("gung", "rieng"), "thin julienned fresh ginger"),
    (("ca chua",), "glossy ripe red tomato wedges"),
    (("ot chuong",), "crisp red and yellow bell pepper chunks"),
    (("dua", "thom", "khom"), "juicy golden pineapple slices"),
    (("nam",), "clusters of fresh oyster and enoki mushrooms"),
    (("ngo", "bap"), "sweet yellow corn rounds"),
    (("mang",), "crisp tender bamboo shoots"),
    (("tac", "quat", "chanh"), "fresh green lime and kumquat slices"),
    (("dao",), "sweet golden peach slices"),
    (("cam",), "fresh bright orange slices"),
]


def _detect_dish_profile(dish: str):
    norm = " " + _strip_accents(dish) + " "
    raw_protein, cooked_protein = "fresh bite-sized main ingredients", "tender glossy cooked pieces"
    for keys, raw_en, cooked_en in INGREDIENT_MAP:
        if any(k in norm for k in keys):
            raw_protein, cooked_protein = raw_en, cooked_en
            break

    vegs = []
    for keys, v_en in VEG_AROMATIC_MAP:
        if any(k in norm for k in keys) and v_en not in vegs:
            vegs.append(v_en)
    if not vegs:
        vegs = ["finely minced garlic and sliced purple shallots", "fresh sliced scallions and red chili"]

    # Classify cooking technique
    if any(k in norm for k in ("tra ", "ca phe", "coffee", "latte", "matcha", "sinh to", "nuoc ep", "sua chua", "che ")):
        tech = "beverage"
    elif any(k in norm for k in ("goi ", "nom ", "sa tac", "tron")):
        tech = "salad_toss"
    elif any(k in norm for k in ("com chien", "com rang", "mi xao", "mien xao", "pho xao", "mi y")):
        tech = "wok_toss"
    elif any(k in norm for k in ("chien", "ran", "rang muoi", "chay toi", "bo toi")):
        tech = "crispy_glaze"
    elif any(k in norm for k in ("kho ", "rim", "om ", "khia")):
        tech = "braise"
    elif any(k in norm for k in ("lau", "canh", "sup", "pho ", "bun ", "mi cay", "hu tieu", "ham", "tan")):
        tech = "soup_hotpot"
    else:
        tech = "stir_fry"

    return {
        "tech": tech,
        "raw_protein": raw_protein,
        "cooked_protein": cooked_protein,
        "primary_aromatic": vegs[0],
        "secondary_veg": vegs[1] if len(vegs) > 1 else "fresh green scallions and crisp herbs",
    }


def _synthesize_general_blueprint(dish: str, region: str) -> dict:
    p = _detect_dish_profile(dish)
    tech = p["tech"]
    raw_p = p["raw_protein"]
    cooked_p = p["cooked_protein"]
    arom = p["primary_aromatic"]
    veg2 = p["secondary_veg"]
    open_p = _dialect_tail(region, "open")
    inv_p = _dialect_tail(region, "invite")
    dish_clean = dish.strip()
    dish_ascii = _strip_accents(dish_clean).title()

    if tech == "beverage":
        dish_en = f"Handcrafted Vietnamese {dish_ascii} refreshing beverage ({raw_p}, {arom})"
        continuity = (
            "The same crystal-clear tall glass and small glass pouring pitchers on a clean white marble kitchen counter. "
            + BASE_KITCHEN_CONTINUITY
            + f"Layered amber-gold tea or rich brew, crystal ice cubes, {arom} and fresh fruit garnish with cool condensation droplets."
        )
        clips = [
            {
                "title": f"{dish_clean} · Ủ cốt nền thơm đậm",
                "start_state": "Clean heatproof glass pitcher on white counter; dry tea/base ingredients and fresh fruit separate.",
                "actions": [
                    "Tilt a glass kettle to pour steaming clear hot water into the glass pitcher holding fragrant tea leaves and aromatics.",
                    "Swirl the warm amber infusion gently once with a long wooden spoon; rich golden color deepens.",
                    f"Drop {arom} from a small clear glass bowl into the warm amber infusion; fragrant oils ripple.",
                    "Pour golden rock-sugar syrup in a thin ribbon into the amber base; smooth swirl catches soft window light.",
                    "Stir gently with the wooden spoon until the golden-amber liquid gleams crystal clear.",
                    "Show close macro of the glossy amber aromatic base resting with delicate wisps of fragrant steam.",
                ],
                "actions_vn": [
                    "Rót nước sôi vào bình thủy tinh ủ cốt nền thơm",
                    "Khuấy nhẹ cho cốt trà lên màu hổ phách trong trẻo",
                    "Thả nguyên liệu thơm tươi vào bình cốt đang ấm",
                    "Rót dòng nước đường phèn vàng óng tạo vị ngọt thanh",
                    "Hòa quyện đều bằng muỗng gỗ cho cốt sánh mượt",
                    "Cận cảnh phần cốt nền trong vắt dậy hương tự nhiên",
                ],
                "voiceover": [
                    _trim_vn_words(f"Pha ngay ly {dish_clean.lower()} mát lạnh tại nhà."),
                    "Ủ cốt nền nóng cho dậy trọn hương thơm tự nhiên.",
                    "Hòa thêm chút đường phèn cho vị ngọt thanh dịu.",
                ],
            },
            {
                "title": f"{dish_clean} · Phối đá lạnh và trái cây",
                "start_state": "Tall crystal-clear serving glass empty on the counter; chilled amber infusion and cut fruit ready.",
                "actions": [
                    "Scoop crystal-clear ice cubes into the tall glass; cubes clink and settle half full.",
                    f"Slide fresh slices of {arom} neatly along the inner glass wall among the clear ice cubes.",
                    "Add more crystal ice cubes nearly to the rim, locking the vibrant fruit slices visibly in place.",
                    "Pour the chilled amber infusion in a steady stream over the ice; liquid cascades through the cubes.",
                    "Pour a splash of tangy citrus juice from a tiny glass spout; subtle color gradient forms.",
                    "Show close macro of cold condensation beads forming on the glass exterior around bright fruit layers.",
                ],
                "actions_vn": [
                    "Cho đá viên trong suốt vào ly thủy tinh cao",
                    "Xếp lát trái cây tươi áp sát thành ly đẹp mắt",
                    "Thêm đá đầy ly giữ các tầng nguyên liệu nổi bật",
                    "Rót dòng cốt trà hổ phách chảy tràn qua từng viên đá",
                    "Điểm chút cốt trái cây tươi cân bằng vị chua ngọt",
                    "Lớp sương lạnh mịn màng phủ quanh thành ly mát rượi",
                ],
                "voiceover": [
                    "Cho đá viên trong suốt cùng lát trái cây tươi.",
                    "Rót dòng cốt đậm đà chảy tràn qua từng viên đá.",
                    "Sắc màu phân tầng đẹp mắt nhìn thôi đã mê.",
                ],
            },
            {
                "title": f"{dish_clean} · Thêm topping và thưởng thức",
                "start_state": "Tall chilled glass filled with amber beverage, ice and fruit slices; toppings ready.",
                "actions": [
                    f"Spoon glossy {veg2} gently onto the top of the iced drink; pieces nestle cleanly on the ice.",
                    "Place a small fresh green mint sprig delicately on top for vibrant contrast.",
                    "Stir the upper layer gently once with a long wooden spoon so cold droplets glisten.",
                    "Show close macro of the finished iced drink: crystal ice, layered amber glow, glossy fruit and mint.",
                    "Lift a glossy fruit piece cleanly from the top of the glass with a slender wooden tasting spoon.",
                    "Hero shot: hold the glossy fruit spoonful just above the SAME chilled glass toward the lens; cold droplets gleam.",
                ],
                "actions_vn": [
                    "Múc phần topping giòn ngọt xếp đầy trên mặt ly",
                    "Điểm nhánh bạc hà xanh mướt tăng hương the mát",
                    "Khuấy nhẹ cho các tầng hương vị hòa quyện mát lành",
                    "Cận cảnh ly đồ uống hoàn chỉnh đọng sương lấp lánh",
                    "Dùng muỗng gỗ nâng miếng topping mọng nước lên",
                    "Đưa miếng topping mát lạnh lại sát ống kính",
                ],
                "voiceover": [
                    "Thêm đầy topping giòn ngọt lên trên mặt ly.",
                    "Điểm lá bạc hà xanh mướt dậy hương thanh mát.",
                    "Khuấy đều mát lạnh sảng khoái, uống là ghiền ngay.",
                ],
            },
        ]
        return {"dish_default": dish_clean, "dish_en": dish_en, "visual_continuity": continuity, "clips": clips}

    if tech == "soup_hotpot":
        dish_en = f"Authentic Vietnamese {dish_ascii} soup/hotpot with {cooked_p} and {arom}"
        continuity = (
            "The same matte warm-ivory deep pot with pale interior. "
            + BASE_KITCHEN_CONTINUITY
            + f"Broth progresses naturally from clear aromatic base to rich savory simmering soup with {cooked_p}, {arom} and {veg2}."
        )
        clips = [
            {
                "title": f"{dish_clean} · Phi thơm và nấu nước dùng",
                "start_state": f"Empty clean warm-ivory pot; {raw_p}, {arom} and broth still separate.",
                "actions": [
                    "Tilt a clear glass bowl and pour a thin golden stream of cooking oil into the warm ivory pot.",
                    f"Drop {arom} from a clear glass bowl into the warm oil; gentle fragrant bubbles appear immediately.",
                    "Stir the aromatics once with the wooden spatula until glossy and fragrant without browning.",
                    "Pour rich clear bone broth steadily from a glass pitcher into the aromatic pot until half full.",
                    "Stir one spoonful of savory seasoning paste into the warm broth; appetizing golden-amber ribbons swirl.",
                    "Show the seasoned broth coming to a gentle simmer with fine bubbles and light translucent steam.",
                ],
                "actions_vn": [
                    "Rót làn dầu vàng óng vào nồi men ngà ấm nóng",
                    "Thả gia vị thơm vào phi sủi tăm dậy mùi",
                    "Đảo nhẹ bằng muôi gỗ cho nguyên liệu nền thơm lừng",
                    "Châm nước dùng xương trong ngọt vào ngập nửa nồi",
                    "Hòa gia vị nêm chuẩn cho màu nước dùng sóng sánh",
                    "Nước dùng sôi lăn tăn bốc làn khói mỏng thơm ngát",
                ],
                "voiceover": [
                    _trim_vn_words(f"Nấu món {dish_clean.lower()} nóng hổi {open_p}."),
                    "Phi thơm nguyên liệu nền cho dậy mùi đặc trưng.",
                    "Châm nước dùng ngọt thanh rồi đun sôi lăn tăn.",
                ],
            },
            {
                "title": f"{dish_clean} · Cho nguyên liệu và thấm vị",
                "start_state": f"Gently simmering seasoned broth with {arom} in the warm-ivory pot; {raw_p} still separate.",
                "actions": [
                    f"Lower {raw_p} piece by piece into the simmering broth using wooden cooking chopsticks.",
                    "Show gentle ripples and fine bubbles surrounding the ingredients as they begin cooking in the hot broth.",
                    f"Show a later cooking moment: {cooked_p} now tender and evenly cooked in the simmering savory broth.",
                    f"Tip {veg2} from a clear glass bowl into the simmering pot; natural splash and vivid color contrast.",
                    "Gently press the fresh ingredients into the hot broth once with the wooden spatula.",
                    "Show close surface macro of the rich simmering soup with glossy oil droplets, tender meat and vegetables.",
                ],
                "actions_vn": [
                    "Dùng đũa gỗ thả nguyên liệu chính tươi ngon vào nồi",
                    "Nước sôi nhẹ ôm trọn từng thớ nguyên liệu ngọt mềm",
                    "Nguyên liệu chín tới lên màu tươi ngon hấp dẫn",
                    "Thêm rau nấm tươi vào nồi nước dùng đang sôi",
                    "Nhấn nhẹ bằng muôi gỗ cho rau thấm vị nước dùng",
                    "Cận cảnh mặt nồi sôi dịu ánh sắc màu bắt mắt",
                ],
                "voiceover": [
                    "Nước sôi đều thì thả nguyên liệu tươi vào nấu.",
                    "Canh lửa vừa để giữ trọn độ mềm ngọt tự nhiên.",
                    "Thêm rau tươi xanh mướt cho nồi canh tròn vị.",
                ],
            },
            {
                "title": f"{dish_clean} · Hoàn thiện nóng hổi",
                "start_state": f"Simmering savory pot with {cooked_p}, {arom} and {veg2} nearly finished.",
                "actions": [
                    "Scatter finely chopped fresh herbs and sliced scallions over the gently bubbling soup surface.",
                    "Add a few thin slices of fresh red chili on top for bright appetizing color.",
                    "Ladle and pour a spoonful of glossy savory broth gently back over the cooked ingredients.",
                    f"Show close macro of the finished {dish_ascii} in the pot: {cooked_p}, vibrant herbs and rich broth.",
                    f"Grip a generous piece of {cooked_p} cleanly with wooden chopsticks inside the simmering pot.",
                    f"Hero shot: wooden chopsticks slowly lift {cooked_p} above the SAME steaming pot toward the lens; savory broth drips back. No serving bowl.",
                ],
                "actions_vn": [
                    "Rắc hành ngò và rau thơm thái nhỏ dậy hương",
                    "Điểm vài lát ớt đỏ tươi tăng sắc màu hấp dẫn",
                    "Múc muỗng nước dùng bóng mượt rưới đều mặt nồi",
                    "Cận cảnh món ăn hoàn chỉnh nóng hổi thơm nức",
                    "Đũa gỗ gắp phần nguyên liệu chín mềm đầy đặn",
                    "Nâng miếng ngon nóng hổi bốc khói sát ống kính",
                ],
                "voiceover": [
                    "Điểm thêm hành ngò tươi cho dậy hương thơm ngát.",
                    "Nước dùng đậm đà quyện cùng nguyên liệu chín mềm.",
                    _trim_vn_words(f"Món ngon nóng hổi ra lò, {inv_p}."),
                ],
            },
        ]
        return {"dish_default": dish_clean, "dish_en": dish_en, "visual_continuity": continuity, "clips": clips}

    if tech == "braise":
        dish_en = f"Vietnamese caramelized braised {dish_ascii} ({cooked_p} in rich amber savory glaze)"
        continuity = (
            "The same matte warm-ivory heavy braising pot with pale interior. "
            + BASE_KITCHEN_CONTINUITY
            + f"Sauce progresses from golden aromatic caramel base to thick glossy amber-brown braising glaze coating {cooked_p}."
        )
    else:
        dish_en = f"Vietnamese {dish_ascii} ({cooked_p} cooked with {arom} and {veg2})"
        continuity = (
            "The same wide matte warm-ivory deep skillet with pale interior. "
            + BASE_KITCHEN_CONTINUITY
            + f"Ingredients progress cleanly from fresh raw state ({raw_p}) to {cooked_p} coated in appetizing glossy savory glaze with {veg2}."
        )

    clips = [
        {
            "title": f"{dish_clean} · Phi thơm và làm săn nguyên liệu",
            "start_state": f"Clean warm-ivory cooking vessel; {raw_p} and {arom} prepared separately in clear glass bowls.",
            "actions": [
                "Tilt a clear glass bowl and pour a thin continuous ribbon of golden oil into the warm ivory vessel.",
                f"Tip {arom} from a clear glass bowl into the shimmering oil; tiny sizzling bubbles appear on contact.",
                "Stir the aromatics once with the wooden spatula until fragrant and glistening without burning.",
                f"Add {raw_p} from a clear glass bowl into the fragrant oil; pieces settle with lively gentle sizzle.",
                "Turn and toss the main ingredients deliberately with wooden chopsticks so surfaces sear lightly golden.",
                "Pour a splash of golden savory seasoning sauce from a small glass bowl; fragrant steam rises.",
            ],
            "actions_vn": [
                "Rót làn dầu vàng óng vào lòng chảo men sáng",
                "Cho hành tỏi gia vị thơm vào phi sủi tăm",
                "Đảo nhẹ bằng muôi gỗ cho dậy hương thơm phức",
                "Thả nguyên liệu chính tươi ngon vào áp chảo săn",
                "Trở đều tay bằng đũa gỗ cho bề mặt vàng đẹp",
                "Nêm lượt sốt đầu tiên cho thấm hương đậm đà",
            ],
            "voiceover": [
                _trim_vn_words(f"Vào bếp làm món {dish_clean.lower()} {open_p}."),
                "Phi thơm gia vị trong làn dầu nóng vàng óng.",
                "Cho nguyên liệu tươi vào đảo săn dậy mùi thơm.",
            ],
        },
        {
            "title": f"{dish_clean} · Phối sốt đậm đà thấm vị",
            "start_state": f"Lightly seared {raw_p} with fragrant {arom} in the same warm-ivory vessel.",
            "actions": [
                "Pour a rich glossy amber-red savory sauce stream from a clear glass bowl over the sizzling ingredients.",
                "Show close macro of the savory sauce bubbling immediately around the seared pieces.",
                "Sweep the wooden spatula steadily to coat every piece evenly in the simmering glossy sauce.",
                f"Tip {veg2} from a clear glass bowl into the simmering savory pan for fresh texture and color.",
                "Fold the vegetables and main ingredients together once with the wooden spatula.",
                f"Show a later cooking moment: {cooked_p} simmering gently as the sauce reduces into a rich glaze.",
            ],
            "actions_vn": [
                "Rưới chén nước sốt pha chuẩn tỉ lệ vào chảo nóng",
                "Nước sốt sôi bùng lên bọt mịn thơm nức gian bếp",
                "Đảo đều để từng miếng thấm đẫm lớp sốt óng ả",
                "Thêm rau củ tươi tạo độ giòn ngọt hài hòa",
                "Đảo nhẹ tay giữ trọn sắc màu tươi tắn tự nhiên",
                "Đun lửa vừa cho nước sốt sánh kẹo thấm sâu",
            ],
            "voiceover": [
                "Rưới đều chén sốt pha chuẩn vị đậm đà.",
                "Thêm rau củ tươi cho món ăn thêm tròn vị.",
                "Đun lửa vừa để sốt sánh lại thấm từng thớ.",
            ],
        },
        {
            "title": f"{dish_clean} · Sánh bóng và gắp thành phẩm",
            "start_state": f"Reduced glossy savory glaze coating {cooked_p} and {veg2} in the same vessel.",
            "actions": [
                f"Show close surface macro of thick glossy glaze bubbling gently around {cooked_p}.",
                "Sprinkle cracked black pepper and finely sliced green scallions lightly over the glossy dish.",
                "Spoon a ribbon of glossy pan glaze directly over the centerpiece ingredient for appetizing shine.",
                f"Show close macro of the finished {dish_ascii}: glistening {cooked_p}, vibrant herbs and rich glaze.",
                f"Grip one prime piece of {cooked_p} cleanly with wooden chopsticks inside the pan.",
                f"Hero shot: wooden chopsticks slowly lift the glossy {cooked_p} above the SAME pan toward the lens; rich glaze gleams. No serving bowl.",
            ],
            "actions_vn": [
                "Cận cảnh lớp sốt kẹo sánh bóng mượt quanh món ăn",
                "Rắc thêm tiêu xay thơm nồng và hành lá xanh mướt",
                "Rưới nhẹ làn sốt bóng lưỡng lên phần thành phẩm",
                "Món ăn hoàn thiện lên màu óng ả cực kỳ bắt mắt",
                "Đũa gỗ gắp miếng thành phẩm mềm ngon đậm sốt",
                "Đưa miếng ngon nóng hổi lại sát ống kính máy quay",
            ],
            "voiceover": [
                "Nước sốt sánh bóng bám đều lên màu cực đẹp.",
                "Rắc thêm chút tiêu hành cho dậy trọn hương thơm.",
                _trim_vn_words(f"Món ngon nóng hổi hoàn tất, {inv_p}."),
            ],
        },
    ]
    return {"dish_default": dish_clean, "dish_en": dish_en, "visual_continuity": continuity, "clips": clips}


def _scale_clips(base_clips: list, dish: str, num_clips: int, region: str) -> list:
    """Adapt a 3-clip blueprint cleanly to 1..6 clips while preserving 6 actions and 3 voiceover lines per clip."""
    num_clips = max(1, min(6, int(num_clips or 3)))
    if num_clips == len(base_clips):
        return base_clips
    if num_clips < len(base_clips):
        if num_clips == 1:
            c1, c2, c3 = base_clips[0], base_clips[1], base_clips[-1]
            return [{
                "title": f"{dish} · Trọn quy trình nấu nhanh",
                "start_state": c1["start_state"],
                "actions": [c1["actions"][0], c1["actions"][3], c2["actions"][0], c2["actions"][3], c3["actions"][4], c3["actions"][5]],
                "actions_vn": [c1["actions_vn"][0], c1["actions_vn"][3], c2["actions_vn"][0], c2["actions_vn"][3], c3["actions_vn"][4], c3["actions_vn"][5]],
                "voiceover": [c1["voiceover"][0], c2["voiceover"][0], c3["voiceover"][2]],
            }]
        if num_clips == 2:
            c1, c2, c3 = base_clips[0], base_clips[1], base_clips[-1]
            return [
                {
                    "title": c1["title"],
                    "start_state": c1["start_state"],
                    "actions": c1["actions"][:4] + c2["actions"][:2],
                    "actions_vn": c1["actions_vn"][:4] + c2["actions_vn"][:2],
                    "voiceover": [c1["voiceover"][0], c1["voiceover"][1], c2["voiceover"][0]],
                },
                {
                    "title": c3["title"],
                    "start_state": c2["start_state"],
                    "actions": c2["actions"][3:5] + c3["actions"][2:],
                    "actions_vn": c2["actions_vn"][3:5] + c3["actions_vn"][2:],
                    "voiceover": [c2["voiceover"][2], c3["voiceover"][0], c3["voiceover"][2]],
                },
            ]

    # Expand to 4..6 clips by adding prep / slow-simmer stages cleanly
    prep_clip = {
        "title": f"{dish} · Sơ chế nguyên liệu tươi",
        "start_state": "Clean white kitchen counter with clear glass prep bowls and wooden cutting board before heating the pot.",
        "actions": [
            "Show close macro of fresh washed main ingredients glistening with tiny water droplets in a clear glass bowl.",
            "Slice fresh aromatic shallots cleanly on a pale wood board with one steady knife stroke.",
            "Crush fresh garlic cloves and chili lightly on the pale wood board; natural oils glisten.",
            "Transfer the freshly cut aromatics neatly into a small clear glass prep bowl.",
            "Stir golden savory seasoning sauce in a small clear glass bowl with a wooden spoon until smooth.",
            "Place the glass prep bowls beside the clean warm-ivory cooking vessel ready for cooking.",
        ],
        "actions_vn": [
            "Cận cảnh nguyên liệu tươi sạch ráo nước trong bát kính",
            "Thái lát hành tím tươi đều tay trên thớt gỗ sáng",
            "Băm nhỏ tỏi ớt tươi dậy hương thơm tự nhiên",
            "Cho phần hành tỏi vừa sơ chế vào chén thủy tinh",
            "Khuấy đều chén nước sốt gia vị sánh mịn chuẩn vị",
            "Bày gọn các chén nguyên liệu cạnh bếp sẵn sàng nấu",
        ],
        "voiceover": [
            f"Chọn nguyên liệu tươi ngon để nấu {dish.lower()}.",
            "Băm nhỏ hành tỏi tươi dậy mùi thơm tự nhiên.",
            "Pha sẵn chén nước sốt đậm đà đúng tỉ lệ.",
        ],
    }
    expanded = [prep_clip] + list(base_clips)
    while len(expanded) < num_clips:
        idx_extra = len(expanded)
        expanded.insert(-1, {
            "title": f"{dish} · Ninh thấm gia vị ({idx_extra})",
            "start_state": expanded[-2]["start_state"],
            "actions": [
                "Show close surface macro of the savory sauce bubbling gently around the cooking ingredients.",
                "Gently turn one centerpiece piece with wooden chopsticks so both sides absorb the rich glaze.",
                "Spoon warm glossy cooking liquid from the pot edge and baste over the top of the ingredients.",
                "Show translucent fragrant steam rising softly across the simmering surface without obscuring detail.",
                "Sweep the wooden spatula slowly along the side to keep the thickening glaze smooth and glossy.",
                "Show the sauce slightly thicker and deeper in color around the tender ingredients.",
            ],
            "actions_vn": [
                "Nước sốt sôi liu riu thấm dần vào từng thớ",
                "Trở nhẹ nguyên liệu bằng đũa gỗ cho ngấm đều hai mặt",
                "Múc nước sốt nóng rưới đều lên mặt món ăn",
                "Làn khói mỏng thơm lừng lan nhẹ trên mặt nồi",
                "Đảo nhẹ giữ lớp sốt sánh mượt không bị bén cạnh",
                "Sắc màu món ăn chuyển đậm đà óng ả hấp dẫn",
            ],
            "voiceover": [
                "Hạ lửa nhỏ cho gia vị thấm sâu từ từ.",
                "Rưới đều nước sốt nóng lên từng miếng ngon.",
                _trim_vn_words(f"Màu sốt sánh mịn nhìn cực kỳ bắt mắt."),
            ],
        })
    return expanded[:num_clips]


def _try_cliproxy_llm_recipe(dish: str, num_clips: int, region: str, custom_notes: str = "") -> dict | None:
    """Attempt fast generation via local CLIProxy (:8317) if running; return None immediately if offline."""
    try:
        with socket.create_connection(("127.0.0.1", 8317), timeout=0.45):
            pass
    except OSError:
        return None

    api_key = "grok-video-key-001"
    for acc_path in (ROOT / "data/google_flow_grok/accounts.json", ROOT / "accounts.json"):
        if acc_path.is_file():
            try:
                for row in json.loads(acc_path.read_text(encoding="utf-8")):
                    if "8317" in str(row.get("proxy_url") or "") and row.get("api_key"):
                        api_key = str(row["api_key"]).strip()
                        break
            except Exception:
                pass

    dialect_hint = (
        "giọng miền Nam thân thiện tự nhiên (nha, nè)"
        if region == "south"
        else ("giọng miền Trung ấm áp gần gũi" if region == "central" else "giọng miền Bắc tự nhiên ấm áp (nhé, chuẩn vị)")
    )
    sys_prompt = (
        "You are a master food-commercial POV director for Google Veo 3.1 (Template 005: 2K 6-panel Storyboard -> 8s Full-Screen POV Cooking Video). "
        "Return ONLY valid JSON (no markdown fences) with keys: "
        "dish_en (English culinary description), "
        "cookware_en (e.g. 'The same matte warm-ivory deep pot with pale interior' or skillet/glass), "
        "visual_progression_en (2 sentences in English locking exact ingredient colors/states across steps, no face/presenter), "
        f"clips (array of EXACTLY {num_clips} clip objects). "
        "Each clip MUST have: "
        "title (short Vietnamese stage title), "
        "start_state (1 English sentence describing exact pot/ingredient state from previous clip), "
        "actions (array of EXACTLY 6 English single-action macro cooking sentences in physical chronological order; final clip action 6 MUST be a hero shot lifting food with wooden chopsticks/spoon above the SAME pot/vessel toward lens, no serving bowl), "
        "actions_vn (array of EXACTLY 6 concise Vietnamese translations matching actions), "
        f"voiceover (array of EXACTLY 3 natural Vietnamese narration sentences, 6 to 9 words each, numbers written as words, {dialect_hint}, NO sales pitch/prices/cart CTA)."
    )
    user_prompt = f"Món ăn: {dish.strip()}" + (f"\nGhi chú thêm: {custom_notes.strip()}" if custom_notes else "")

    for model_name in ("gemini-2.5-flash", "gpt-4o-mini", "gpt-4o"):
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.35,
                "max_tokens": 2600,
            }
            req = urllib.request.Request(
                "http://127.0.0.1:8317/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=16) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
            content = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
            m = re.search(r"\{[\s\S]*\}", content)
            parsed = json.loads(m.group(0) if m else content)
            clips = parsed.get("clips") or []
            if len(clips) != num_clips:
                continue
            valid_clips = []
            for idx, c in enumerate(clips, 1):
                acts = [str(x).strip() for x in (c.get("actions") or []) if str(x).strip()]
                vo = [_trim_vn_words(str(x).strip(), 12) for x in (c.get("voiceover") or []) if str(x).strip()]
                if len(acts) != 6 or len(vo) != 3:
                    valid_clips = []
                    break
                acts_vn = [str(x).strip() for x in (c.get("actions_vn") or []) if str(x).strip()]
                if len(acts_vn) != 6:
                    acts_vn = acts
                valid_clips.append({
                    "title": str(c.get("title") or f"{dish} · Đoạn {idx}").strip(),
                    "start_state": str(c.get("start_state") or "Clean pot; ingredients prepared separately.").strip(),
                    "actions": acts,
                    "actions_vn": acts_vn,
                    "voiceover": vo,
                })
            if not valid_clips:
                continue
            cookware = str(parsed.get("cookware_en") or "The same matte warm-ivory pot with pale interior").strip().rstrip(".")
            prog = str(parsed.get("visual_progression_en") or "").strip()
            return {
                "dish": dish.strip(),
                "dish_en": str(parsed.get("dish_en") or dish.strip()).strip(),
                "visual_continuity": f"{cookware}. {BASE_KITCHEN_CONTINUITY}{prog}".strip(),
                "clips": valid_clips,
                "generator_source": f"cliproxy:{model_name}",
            }
        except Exception:
            continue
    return None


def generate_cooking_recipe_and_script(
    dish: str = "",
    num_clips: int = 3,
    audio_mode: str = "voice",
    voice_id: str = "",
    voice_meta: dict | None = None,
    custom_notes: str = "",
    prefer_llm: bool = True,
    *,
    dish_name: str = "",
    voice_region: str = "",
    prefer_ai: bool | None = None,
) -> dict:
    """
    Generate a complete Template 005 recipe + 6-shot macro actions + 3-beat Vietnamese voiceover
    from just a dish name and optional voice metadata.
    """
    dish_clean = str(dish or dish_name or "").strip() or "Lẩu Thái tôm nấm"
    if prefer_ai is not None:
        prefer_llm = bool(prefer_ai)
    num_clips = max(1, min(6, int(num_clips or 3)))
    audio_mode = "voice" if str(audio_mode or "").lower() == "voice" else "asmr"
    voice_meta = dict(voice_meta or {})
    region = str(voice_region or voice_meta.get("region") or "north").lower()

    norm_dish = _strip_accents(dish_clean)
    curated = _curated_blueprints(region)

    blueprint = None
    generator_source = "culinary_director_v2"

    # Match curated flagship dish blueprints first if exact/close match and no custom override notes
    if not str(custom_notes or "").strip():
        for key_pat, bp in curated.items():
            if key_pat in norm_dish:
                blueprint = bp
                generator_source = f"curated_v2:{key_pat.replace(' ', '_')}"
                break

    if blueprint is None and prefer_llm:
        llm_res = _try_cliproxy_llm_recipe(dish_clean, num_clips=num_clips, region=region, custom_notes=custom_notes)
        if llm_res:
            llm_res["audio_mode"] = audio_mode
            llm_res["voice_id"] = str(voice_id or voice_meta.get("voice_id") or "").strip()
            if voice_meta.get("key"):
                llm_res["voice_key"] = voice_meta["key"]
            if voice_meta.get("name"):
                llm_res["voice_name"] = voice_meta["name"]
            return llm_res

    if blueprint is None:
        blueprint = _synthesize_general_blueprint(dish_clean, region)

    scaled_clips = _scale_clips(blueprint["clips"], dish_clean, num_clips, region)
    out_clips = []
    for cl in scaled_clips:
        item = {
            "title": cl["title"],
            "start_state": cl["start_state"],
            "actions": list(cl["actions"]),
            "actions_vn": list(cl.get("actions_vn") or cl["actions"]),
            "voiceover": [_trim_vn_words(v, 12) for v in (cl.get("voiceover") or [])],
        }
        out_clips.append(item)

    result = {
        "dish": dish_clean,
        "dish_en": blueprint["dish_en"],
        "visual_continuity": blueprint["visual_continuity"],
        "audio_mode": audio_mode,
        "voice_id": str(voice_id or voice_meta.get("voice_id") or "").strip() if audio_mode == "voice" else "",
        "clips": out_clips,
        "generator_source": generator_source,
    }
    if audio_mode == "voice":
        if voice_meta.get("key"):
            result["voice_key"] = voice_meta["key"]
        if voice_meta.get("name"):
            result["voice_name"] = voice_meta["name"]
    return result
