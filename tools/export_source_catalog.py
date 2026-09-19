"""Export reviewed public metadata from an ELMA-IoT Windows source checkout."""
from __future__ import annotations
import argparse, importlib, json, re, sys
from pathlib import Path

def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--windows", required=True, type=Path)
    parser.add_argument("--output", default=Path("data/catalog.json"), type=Path)
    args=parser.parse_args()
    root=args.windows.resolve(); sys.path.insert(0,str(root))
    registry=importlib.import_module("logic_registry")
    helpmod=importlib.import_module("logic_help")
    source=json.loads((root/"native_designer_catalog.json").read_text(encoding="utf-8"))
    nodes=[]
    for node_id,node in sorted(registry.REGISTRY.items()):
        purpose,example=helpmod.explanation(node,node)
        nodes.append({"nodeId":node_id,"helpId":node["helpId"],"title":node["title"],
          "category":node["category"],"description":node.get("description",purpose),
          "purpose":purpose,"example":example,"ports":node.get("ports",[]),
          "parameters":node.get("parameters",{}),"binding":node.get("binding"),
          "technicalReview":purpose.startswith("Uses the typed connectors")})
    labels={}
    for group in source["groups"]:
        for option in group["options"]: labels[group["key"]+":"+option["value"]]=option["label"]
    profile_values=[key.split(':',1)[1] for key in source["profiles"] if not key.endswith(':none')]
    duplicated={value for value in profile_values if profile_values.count(value)>1}
    peripherals=[]
    for profile_id,profile in sorted(source["profiles"].items()):
        group,value=profile_id.split(":",1)
        if value=="none": continue
        topic=(group+'-'+value) if value in duplicated else value
        peripherals.append({"peripheralId":profile_id,"helpId":"peripheral."+slug(topic),
          "title":labels.get(profile_id,value.replace("-"," ").title()),"group":group,
          "signals":profile.get("signals",[]),"pins":profile.get("pins",[]),
          "requirements":profile.get("requirements",{}),"rails":profile.get("rails",{})})
    boards=[]
    for board_id,board in sorted(source["boards"].items()):
        pins=[]
        for area in ("layout","extras"):
            for side in ("left","right"): pins.extend(board.get(area,{}).get(side,[]))
        boards.append({"boardId":board_id,"helpId":"boards."+slug(board_id),
          "title":board_id.replace("-"," ").upper(),"chip":board.get("chip"),"pins":pins,
          "reserved":board.get("reserved",{}),"assetAlt":board.get("asset",{}).get("alt","")})
    payload={"schemaVersion":1,"appliesTo":{"android":"1.0.13+","windows":"0.1.57+","firmware":"0.1.54+"},
      "locales":["en","es","zh","hi","ar","pt","bn","ru","ja","de","fr","ko","tr","it","id","pl","uk","vi","th","fa"],
      "nodes":nodes,"peripherals":peripherals,"boards":boards}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Exported {len(nodes)} nodes, {len(peripherals)} peripherals, {len(boards)} boards")

if __name__=="__main__": main()
