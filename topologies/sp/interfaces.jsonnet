{
    p11: [
        { network: "p11_p21" },
        { network: "p11_p22" },
        { network: "p11_pe11" },
        { network: "p11_pe12" },
        { network: "p11_p12" },
    ],
    p12: [
        { network: "p12_p22" },
        { network: "p12_p21" },
        { network: "p12_pe11" },
        { network: "p12_pe12" },
        { network: "p11_p12" },
    ],
    p21: [
        { network: "p11_p21" },
        { network: "p12_p21" },
        { network: "p21_pe21" },
        { network: "p21_pe22" },
        { network: "p21_p22" },
    ],
    p22: [
        { network: "p12_p22" },
        { network: "p11_p22" },
        { network: "p22_pe21" },
        { network: "p22_pe22" },
        { network: "p21_p22" },
    ],
    pe11: [
        { network: "p11_pe11" },
        { network: "p12_pe11" },
        { network: "pe11_pe12" },
        { network: "pe11_pe21" },
        { network: "h11" },
    ],
    pe12: [
        { network: "p11_pe12" },
        { network: "p12_pe12" },
        { network: "pe11_pe12" },
        { network: "pe12_pe22" },
        { network: "h12" },
    ],
    pe21: [
        { network: "p21_pe21" },
        { network: "p22_pe21" },
        { network: "pe21_pe22" },
        { network: "pe11_pe21" },
        { network: "h21" },
    ],
    pe22: [
        { network: "p21_pe22" },
        { network: "p22_pe22" },
        { network: "pe21_pe22" },
        { network: "pe12_pe22" },
        { network: "h22" },
    ],
    h11: [
        { bridge: "mgmt" },
        { network: "h11" },
    ],
    h12: [
        { bridge: "mgmt" },
        { network: "h12" },
    ],
    h21: [
        { bridge: "mgmt" },
        { network: "h21" },
    ],
    h22: [
        { bridge: "mgmt" },
        { network: "h22" },
    ],
}