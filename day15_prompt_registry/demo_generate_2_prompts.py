#
# Demo generate 2 versions prompts
from registry.registry import PromptRegistry

if __name__ == "__main__":
    reg = PromptRegistry("prompts")

    print("Versions:", reg.list_versions())
    print("Prompts in v1:", reg.list_prompts("v1"))

    faq_v1 = reg.render(
        "faq", "v1",
        context="VPN 文件路徑：/docs/vpn/setup",
        question="公司 VPN 怎麼設定？"
    )
    print("\n[FAQ v1]\n", faq_v1)

    faq_v2 = reg.render(
        "faq", "v2",
        context="VPN 文件路徑：/docs/vpn/setup",
        question="公司 VPN 怎麼設定？"
    )
    print("\n[FAQ v2]\n", faq_v2)
