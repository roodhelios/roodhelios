<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="banner-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="banner-light.svg">
  <img src="banner-dark.svg" width="100%" alt="profile.sh --live">
</picture>

<br/>

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=22&duration=3200&pause=900&color=4EA8DE&center=true&vCenter=true&width=700&lines=Building+Zero+Trust+authorization+for+AI+agents;Hardening+AWS+at+production+scale;Reverse-engineering+malware+for+fun;Never+trust.+Always+verify." alt="Typing SVG" />

<br/>

[![Portfolio](https://img.shields.io/badge/Portfolio-0F4C81?style=for-the-badge&logo=firefox-browser&logoColor=white)](https://roodhelios.github.io/Portfolio.github.io/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/aryan-singh-rootkid)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:Aryanpratapsingh1912@gmail.com)
![Profile views](https://komarev.com/ghpvc/?username=roodhelios&style=for-the-badge&color=0F4C81)

</div>

---

## `whoami`

```
Aryan Singh — Security Engineer
├── now      : M.S. Cybersecurity @ Northeastern University (Khoury)
├── before   : 15 months securing production AWS + a 40-server hybrid fleet
├── building : Zero Trust authorization for autonomous AI agents
├── into     : cloud IAM, detection engineering, malware reverse engineering
└── seeking  : Summer 2027 security engineering co-op
```

- Spent 15 months as a Security Engineer rebuilding IAM around least privilege across 6 AWS accounts, segmenting VPCs, and hardening Linux/Windows fleets.
- Now focused on a problem I think is underbuilt: **autonomous AI agents get permanent trust after one login.** That's a terrible security model, so I'm building the alternative.
- Comfortable on both sides of the line — I write policy engines and I also take apart packed PE32 loaders in FLARE-VM.

---

## Featured Work

<table>
<tr>
<td width="50%" valign="top">

### Aegis
**Zero Trust control plane for autonomous AI agents**

Every tool call an agent makes is authorized before it executes — identity verified, request signed, risk scored, policy evaluated.

`Python` `FastAPI` `OPA/Rego` `PostgreSQL` `Redis` `Ed25519`

_Private repository_

</td>
<td width="50%" valign="top">

### Digital Footprint Risk Visualizer
**Attack surface & vulnerability intelligence platform**

Four scanners orchestrated behind one authenticated control layer, each sandboxed, findings normalized into a single severity-ranked view.

`React` `Node.js` `MongoDB` `Docker` `JWT` `TOTP MFA`

[Repo →](https://github.com/roodhelios/Digital-Footprint-Analyzer)

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Artemis / TSULoader Analysis
**Malware reverse engineering**

Static and dynamic teardown of a packed PE32 loader — high-entropy section analysis through to the dropped DLL payload.

`FLARE-VM` `IDA Pro` `capa` `Procmon` `FakeNet-NG`

_Writeup coming_

</td>
<td width="50%" valign="top">

### Network Threat Detection
**GRU-LSTM traffic anomaly model**

Hybrid recurrent model on temporal flow features, detecting DDoS and MITM-associated traffic at ~92% accuracy.

`TensorFlow` `Keras` `Pandas` `AWS Lambda`

_Repo coming_

</td>
</tr>
<tr>
<td colspan="2" valign="top">

### Zero Shadow — Autonomous Asset Intelligence
**Local-first asset correlation & explainable security risk engine**

Correlates explicitly scoped asset observations from multiple sources into stable asset identities while preserving source evidence. Built around deterministic matching, safe fixture-driven development, and explainable risk scoring rather than opaque discovery.

`Python` `Asset Correlation` `Risk Scoring` `Security Automation` `Deterministic Tests`

[Repo →](https://github.com/roodhelios/zero-shadow-autonomous-asset-intelligence)

</td>
</tr>
</table>

---

## Toolkit

<details open>
<summary><b>Security Engineering &amp; IAM</b></summary>
<br/>

![Zero Trust](https://img.shields.io/badge/Zero_Trust-0F4C81?style=flat-square)
![OPA](https://img.shields.io/badge/Open_Policy_Agent-7D9199?style=flat-square&logo=openpolicyagent&logoColor=white)
![Rego](https://img.shields.io/badge/Rego-566270?style=flat-square)
![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white)
![Ed25519](https://img.shields.io/badge/Ed25519-4A4A4A?style=flat-square)
![MFA](https://img.shields.io/badge/TOTP_MFA-2D6A4F?style=flat-square)

</details>

<details>
<summary><b>Cloud &amp; Infrastructure</b></summary>
<br/>

![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazonwebservices&logoColor=white)
![IAM](https://img.shields.io/badge/IAM-FF9900?style=flat-square&logo=amazoniam&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-844FBA?style=flat-square&logo=terraform&logoColor=white)

</details>

<details>
<summary><b>Detection &amp; Network Security</b></summary>
<br/>

![Splunk](https://img.shields.io/badge/Splunk-000000?style=flat-square&logo=splunk&logoColor=white)
![Suricata](https://img.shields.io/badge/Suricata-EE2A35?style=flat-square&logo=suricata&logoColor=white)
![Zeek](https://img.shields.io/badge/Zeek-4B8BBE?style=flat-square)
![Wireshark](https://img.shields.io/badge/Wireshark-1679A7?style=flat-square&logo=wireshark&logoColor=white)
![Scapy](https://img.shields.io/badge/Scapy-0B5394?style=flat-square)
![iptables](https://img.shields.io/badge/iptables-D62828?style=flat-square)

</details>

<details>
<summary><b>Offensive Security &amp; Malware RE</b></summary>
<br/>

![Kali](https://img.shields.io/badge/Kali_Linux-557C94?style=flat-square&logo=kalilinux&logoColor=white)
![Burp](https://img.shields.io/badge/Burp_Suite-FF6633?style=flat-square&logo=burpsuite&logoColor=white)
![OWASP ZAP](https://img.shields.io/badge/OWASP_ZAP-00549E?style=flat-square&logo=owasp&logoColor=white)
![IDA Pro](https://img.shields.io/badge/IDA_Pro-1E1E1E?style=flat-square)
![Ghidra](https://img.shields.io/badge/Ghidra-5B2C6F?style=flat-square)
![capa](https://img.shields.io/badge/capa-6C3483?style=flat-square)
![FLARE-VM](https://img.shields.io/badge/FLARE--VM-B03A2E?style=flat-square)

</details>

<details>
<summary><b>Languages</b></summary>
<br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Bash](https://img.shields.io/badge/Bash-4EAA25?style=flat-square&logo=gnubash&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-4479A1?style=flat-square&logo=postgresql&logoColor=white)
![C](https://img.shields.io/badge/C-00599C?style=flat-square&logo=c&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)

</details>

---

## Stats

<div align="center">

<img height="165" src="https://github-stats-extended.vercel.app/api?username=roodhelios&show_icons=true&hide_border=true&theme=tokyonight&bg_color=0D1117&title_color=4EA8DE&icon_color=4EA8DE&text_color=C9D1D9" alt="GitHub stats" />
<img height="165" src="https://github-stats-extended.vercel.app/api/top-langs/?username=roodhelios&layout=compact&hide=html,css&hide_border=true&theme=tokyonight&bg_color=0D1117&title_color=4EA8DE&text_color=C9D1D9" alt="Top languages" />

</div>

---

<div align="center">

**Never trust. Always verify.**

</div>
