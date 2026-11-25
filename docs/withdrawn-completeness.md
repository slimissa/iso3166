# Withdrawn list against ISO 3166-3

Status as of v1.12.14 (recheck 2027-02-25). This page compares the
registry's 25 withdrawn entries with ISO 3166-3, the ISO list of formerly
used country names, and with ISO's reserved alpha-2 codes. It changes no
data: the withdrawn list (its rows, alpha-2 keys and `withdrawal_date`
values) stays as it is until a decision record settles the modelling
questions below.

## Sources

Every one of the 31 ISO 3166-3 entries has an ISO page here. They are the
maintainer's Firefox saves of the ISO Online Browsing Platform (OBP), made on
2026-11-25:

- 22 pages of entries with the status "Formerly used" (`obp-3166-3/`);
- 9 pages of reserved alpha-2 codes, each also an ISO 3166-3 entry: AN, BU,
  CS, NT, TP, YU, ZR ("Transitionally reserved") and FX, SU ("Exceptionally
  reserved") (`obp-reserved/`).

Each page shows its alpha-2 and alpha-4 code, names, status, "Remark part 3"
(what the name became) and a "Change history" table. The code shown on every
page matches its file name. Five pages (BQAQ, BYAA, CSHH, GEHH, PUUM) were
saved after the first `SHA256SUMS` was written; the maintainer regenerated
the sums on 2026-11-25, and every page now matches it (listed at the end).

The ISO 3166-3 newsletters I-1 to I-5 (2002–2006, Internet Archive captures
of the ISO 3166/MA website) add a period of validity for four entries.

Nothing on this page rests on Wikipedia any more: ISO pages exist for every
entry.

## Counts

| | Entries |
|--|--:|
| ISO 3166-3 entries, each with an ISO page | 31 |
| In the registry's withdrawn list | 25 |
| In both | 25 |
| ISO entries not in the registry | 6: BQAQ, BYAA, CSHH, FXFR, GEHH, PUUM |
| Registry rows not in ISO 3166-3 | 0 |

Of the 25 registry rows, compared on the withdrawal date:

| Result | Rows |
|--------|-----:|
| Agrees with a date on the ISO page or in a Part 3 newsletter | 6 (CSXX and YUCS exactly; BUMM, NTHH and TPTL to the month; SUHH to the year) |
| Differs | 2 (ANHH, ZRCD) |
| No date on the ISO page to compare with | 17 |

## Per entry

"ISO dates" lists every dated statement on the entry's ISO page: the reserved
period, a year in "Remark part 3", each change-history line, and the period
of validity from a Part 3 newsletter.

| ISO 3166-3 | Alpha-2 | Name (ISO) | ISO status | ISO dates | Registry `withdrawal_date` | Comparison |
|------------|---------|------------|------------|-----------|----------------------------|------------|
| AIDJ | AI | French Afars and Issas | Formerly used | — | 1977-06-27 | no ISO date on the page |
| ANHH | AN | Netherlands Antilles | Transitionally reserved | Reserved from 2010-12 to 2060-12; 2011-12-13 "Deletion of code to align ISO 3166-1 and ISO 3166-2."; 2011-07-14 "Correct the English name to Sint Eustatius in alignment with United Na…"; 2011-03-14 "Divided into: Bonaire, Saint Eustatius and Saba (BQ, BES, 535), Curaça…"; 2010-12-15 "Delete entry" | 2010-12-01 | **differs**: ISO 2010-12-15 |
| BQAQ | BQ | British Antarctic Territory | Formerly used | — | — | not in registry |
| BUMM | BU | Burma | Transitionally reserved | Reserved from 1989-12 to 2039-12 | 1989-12-05 | agrees (month: 1989-12) |
| BYAA | BY | Byelorussian SSR | Formerly used | — | — | not in registry |
| CSHH | CS | Czechoslovakia | Formerly used | — | — | not in registry |
| CSXX | CS | Serbia and Montenegro | Transitionally reserved | Reserved from 2006-09 to 2056-09; 2006-12-01 "Divided into: Serbia (RS, SRB, 688), and Montenegro (ME, MNE, 499)"; 2006-09-26 "Divided into: Serbia (RS, SRB, 688), and Montenegro (ME, MNE, 499)"; Part 3 period 2003/2006 (I-4, 2006-09-26; I-5, 2006-12-01) | 2006-09-26 | agrees (exact: 2006-09-26) |
| CTKI | CT | Canton and Enderbury Islands | Formerly used | — | 1984-01-01 | no ISO date on the page |
| DDDE | DD | German Democratic Republic | Formerly used | — | 1990-10-03 | no ISO date on the page |
| DYBJ | DY | Dahomey | Formerly used | — | 1977-02-01 | no ISO date on the page |
| FQHH | FQ | French Southern and Antarctic Territories | Formerly used | — | 1979-01-01 | no ISO date on the page |
| FXFR | FX | France, Metropolitan | Exceptionally reserved | 2002-11-22 "Deleted; see France (FR, FRA, 250) in ISO 3166-1"; Part 3 period 1993/1997 (I-2, 2002-11-22) | — | not in registry |
| GEHH | GE | Gilbert and Ellice Islands | Formerly used | — | — | not in registry |
| HVBF | HV | Upper Volta | Formerly used | — | 1984-08-04 | no ISO date on the page |
| JTUM | JT | Johnston Island | Formerly used | — | 1986-01-01 | no ISO date on the page |
| MIUM | MI | Midway Islands | Formerly used | — | 1986-01-01 | no ISO date on the page |
| NHVU | NH | New Hebrides | Formerly used | — | 1980-07-30 | no ISO date on the page |
| NQAQ | NQ | Dronning Maud Land | Formerly used | — | 1983-01-01 | no ISO date on the page |
| NTHH | NT | Neutral Zone | Transitionally reserved | Reserved from 1993-07 to 2043-07 | 1993-07-01 | agrees (month: 1993-07) |
| PCHH | PC | Pacific Islands (Trust Territory) | Formerly used | — | 1986-11-03 | no ISO date on the page |
| PUUM | PU | United States Miscellaneous Pacific Islands | Formerly used | — | — | not in registry |
| PZPA | PZ | Panama Canal Zone | Formerly used | — | 1980-01-01 | no ISO date on the page |
| RHZW | RH | Southern Rhodesia | Formerly used | — | 1980-04-18 | no ISO date on the page |
| SKIN | SK | Sikkim | Formerly used | — | 1975-05-16 | no ISO date on the page |
| SUHH | SU | USSR | Exceptionally reserved | Remark part 3: "Removed from ISO 3166-1 in 1992"; 2017-03-17 "Deletion of "Republic of" in front of (MD, MDA, 498) in the Remark Par…" | 1992-08-30 | agrees (year: 1992) |
| TPTL | TP | East Timor | Transitionally reserved | Reserved from 2002-05 to 2052-05; 2002-11-15 "Timor-Leste (TL, TLS, 626)"; Part 3 period 1974/2002 (I-1, 2002-11-15) | 2002-05-20 | agrees (month: 2002-05) |
| VDVN | VD | Viet-Nam, Democratic Republic of | Formerly used | — | 1976-07-02 | no ISO date on the page |
| WKUM | WK | Wake Island | Formerly used | — | 1986-01-01 | no ISO date on the page |
| YDYE | YD | Yemen, Democratic | Formerly used | — | 1990-05-22 | no ISO date on the page |
| YUCS | YU | Yugoslavia | Transitionally reserved | Reserved from 2003-07 to 2053-07; Remark part 3: name changed "in 2003"; 2003-07-23 "Serbia and Montenegro (CS, SCG, 891)"; Part 3 period 1974/2003 (I-3, 2003-07-23) | 2003-07-23 | agrees (exact: 2003-07-23) |
| ZRCD | ZR | Zaire | Transitionally reserved | Reserved from 1997-07 to 2047-07 | 1997-05-17 | **differs**: ISO reserved from 1997-07 |

## The two differences

- **AN (Netherlands Antilles).** The registry has 2010-12-01. ISO's change
  history has "2010-12-15 Delete entry", and the AN reservation starts in
  2010-12. ISO's date is 2010-12-15.
- **ZR (Zaire).** The registry has 1997-05-17. ISO reserves ZR "from
  1997-07", so ISO's change falls in July 1997, not May.

Neither is changed here (decision D6 of this work: the withdrawn list stays).

## Other differences in the rows the registry holds

| Entry | Field | ISO page | Registry |
|-------|-------|----------|----------|
| YUCS | numeric | 891 | 890 |
| CTKI, JTUM, MIUM, NQAQ, NTHH, PCHH, WKUM | numeric | 128, 396, 488, 216, 536, 582, 872 | `000` (no numeric held) |
| DDDE | name | German Democratic Republic | East Germany |
| VDVN | name | Viet-Nam, Democratic Republic of | North Vietnam |
| YDYE | name | Yemen, Democratic | South Yemen |
| SUHH | successors | AM, AZ, EE, GE, KZ, KG, LV, LT, MD, RU, TJ, TM, UZ ("Remark part 3") | `replaced_by: null` |

YU's numeric 891 is also the one Newsletter V-8 (2003-07-23) shows for
Yugoslavia and keeps for Serbia and Montenegro.

## What ISO says each name became ("Remark part 3")

| ISO 3166-3 | Remark part 3 |
|------------|---------------|
| AIDJ | Name changed from French Afars and Issas to Djibouti (DJ, DJI, 262). |
| ANHH | The Netherlands Antilles was divided into Bonaire, Saint Eustatius and Saba (BQ, BES, 535), Curaçao (CW, CUW, 531) and Sint Maarten (Dutch part) (SX, SXM, 534). |
| BQAQ | British Antarctic Territory is now part of the entry Antarctica (AQ, ATA, 010). |
| BUMM | Name changed from former Burma (BU, BUR, 104) to Myanmar (MM MMR, 104). See code element BUMM. |
| BYAA | Name changed to Belarus (BY, BLR, 112). Code element BYS removed from ISO 3166-1. |
| CSHH | Czechoslovakia was divided into Czechia (CZ, CZE, 203), and Slovakia (SK, SVK, 703). |
| CSXX | Formerly part of Yougoslavia (YU, YUG, 891) before its split. See code element YUCS. Name changed from former Yugoslavia (YU, YUG, 891) to Serbia and Montenegro (CS, SCG, 891). See also code element YUCS. Serbia and Montenegro was then divided into Serbia (RS, SRB, 688) and Montenegro (ME, MNE, 499). |
| CTKI | Now part of Kiribati (KI, KIR, 296). |
| DDDE | Now part of code entry for Germany (DE, DEU, 276). |
| DYBJ | Name changed to Benin (BJ, BEN, 204). |
| FQHH | French Southern and Antarctic Territories are now part of Antarctica (AQ, ATA, 010) and French Southern Territories (TF, ATF, 260). |
| FXFR | Metropolitan France is now incorporated into the entry for France (FR, FRA, 250). |
| GEHH | The Gilbert and Ellice Islands were divided into: Gilbert Islands: Kiribati (KI, KIR, 296), and Ellice Islands: Tuvalu (TV, TUV, 798). |
| HVBF | Name changed from Upper Volta to Burkina Faso (BF, BFA, 854). |
| JTUM | Johnston Island is now incorporated in the entry for US Minor Outlying Islands (UM, UMI, 581). |
| MIUM | Midway Islands are now incorporated in the entry for US Minor Outlying Islands (UM, UMI, 581). |
| NHVU | Name changed from New Hebrides to Vanuatu (VU, VUT, 548). |
| NQAQ | Now part of Antarctica (AQ, ATA, 010). |
| NTHH | The Neutral Zone (NT, NTZ, 536) was divided and is now part of Iraq (IQ, IRQ, 368) and part of Saudi Arabia (SA, SAU, 682). The code entry (NT, NTZ, 536) was deleted from ISO 3166-1. |
| PCHH | Pacific Islands (Trust Territory) were divided into: Marshall Islands (MH, MHL, 584), Micronesia, Federated States of (FM, FSM, 583), Northern Mariana Islands (MP, MNP, 580) and Palau (PW, PLW, 585). |
| PUUM | United States Miscellaneous Pacific Islands are now part of the entry for US Minor Outlying Islands (UM, UMI, 581). |
| PZPA | The Zone of the Panama Canal is now part of the entry for Panama (PA, PAN, 591). |
| RHZW | Name changed from Southern Rhodesia (RH, RHO, --) to Zimbabwe (ZW, ZWE, 716). |
| SKIN | Sikkim is now part of the entry for India (IN, IND, 356). |
| SUHH | Removed from ISO 3166-1 in 1992 when former USSR was divided into: Armenia (AM, ARM, 051), Azerbaijan (AZ, AZE, 031), Estonia (EE, EST, 233), Georgia (GE, GEO, 268), Kazakstan (KZ, KAZ, 398), Kyrgyzstan (KG, KGZ, 417), Latvia (LV, LVA, 428), Lithuania (LT, LTU, 440), Republic of Moldova (MD, MDA, 498), Russian Federation (RU, RUS, 643), Tajikistan (TJ, TJK, 762), Turkmenistan (TM, TKM, 795), Uzbekistan (UZ, UZB, 860). NOTE: Belarus (BY, BLR, 112) and Ukraine (UA, UKR, 804) are not listed because they were separately coded in ISO 3166 already before the USSR was split. |
| TPTL | Name changed from East Timor (TP, TMP, 626) to Timor-Leste (TL, TLS, 626). |
| VDVN | The former Democratic Republic of Viet-Nam is now part of the entry for Viet Nam (VN, VNM, 704). |
| WKUM | Wake Island (WK, WAK, 872) is now part of the entry for US Minor Outlying Islands (UM, UMI, 581). |
| YDYE | The Democratic Yemen is now part of the entry Yemen (YE, YEM, 887). |
| YUCS | Name changed from Yugoslavia to Serbia and Montenegro (CS, SCG, 891) in 2003. Former Yugoslavia was divided into Bosnia and Herzegovina (BA), Croatia (HR),The former Yugoslav Republic of Macedonia (MK), Serbia and Montenegro (CS), Slovenia (SI). |
| ZRCD | Name changed from Zaire to the Democratic Republic of the Congo (CD, COD, 180). See also code element ZRCD. |

## What the Part 3 newsletters add

| Newsletter | Date | Entry | Period of validity | What it records |
|------------|------|-------|--------------------|-----------------|
| I-1 | 2002-11-15 | TPTL, East Timor (TP, TMP, 626) | 1974/2002 | TP moves to ISO 3166-3 when the name becomes Timor-Leste (TL). Note: "From 1974 to 1977 East Timor was included in ISO 3166 under the name of Portuguese Timor (TP,TMP)." |
| I-2 | 2002-11-22 | FXFR, France, Metropolitan (FX, FXX, 249) | 1993/1997 | Added as a correction: the entry was "inadvertently omitted from ISO 3166-3 when first published in 1999". This is the FX page's only change-history line. |
| I-3 | 2003-07-23 | YUCS, Yugoslavia (YU, YUG, 891) | 1974/2003 | YU moves to ISO 3166-3 when Serbia and Montenegro takes CS (the same day as ISO 3166-1 Newsletter V-8). |
| I-4 | 2006-09-26 | Serbia and Montenegro (CS, SCG, 891) | 2003/2006 | Divided into RS and ME. I-4 gave it the alpha-4 CSHH. |
| I-5 | 2006-12-01 | CSXX | 2003/2006 | Corrects I-4: CSHH already belonged to Czechoslovakia, so Serbia and Montenegro is CSXX. The CS page's two change-history lines (2006-09-26 and 2006-12-01) are these two newsletters. |

The periods give years only. None is a full date, so none dates a withdrawn
row's start; I-4 and I-5 corroborate the start year of CS (2003), which
ISO 3166-1 Newsletter V-8 dates to 2003-07-23.

## "Exceptionally reserved": FX and SU

ISO gives two former entries the status "Exceptionally reserved", with a
reason: FX "reserved at the request of France", SU "reserved at the request of
the Foundation for Internet Development (FID)". The other seven reserved codes
saved here (AN, BU, CS, NT, TP, YU, ZR) are "Transitionally reserved" for 50
years from their withdrawal (for example BU "from 1989-12 to 2039-12").

The registry models these two cases differently from each other and from
ISO:

- **SU** is a withdrawn row (`withdrawal_date` 1992-08-30, `replaced_by`
  null). Nothing in it says the code stays reserved, or why.
- **FX** is not in the registry at all, although ISO 3166-1 carried it from
  1993 to 1997 and still reserves it.
- **EU** and **UK**, which ISO also reserves exceptionally, are the
  registry's only rows with that status, and they are active rows
  (`status: exceptionally-reserved`). They were never ISO 3166-1 country
  entries; SU and FX were.

So "exceptionally reserved" in ISO cuts across the registry's split between
active and withdrawn. Options for the maintainer: keep SU and FX as withdrawn
rows and add a reservation note; add a reservation field to withdrawn rows
(a schema change); or record reservations in a separate list. Each needs a
decision record; this page makes none.

## The six entries the registry lacks

| ISO 3166-3 | Name (ISO) | Alpha-2 | Collides with | Note |
|------------|------------|---------|---------------|------|
| BQAQ | British Antarctic Territory | BQ | active `BQ` (Bonaire, Sint Eustatius and Saba) | ISO, Remark part 1: BQ "has been reused and reassigned" |
| BYAA | Byelorussian SSR | BY | active `BY` (Belarus) | ISO: "Name changed to Belarus (BY, BLR, 112). Code element BYS removed": the alpha-2 stayed, the alpha-3 changed |
| CSHH | Czechoslovakia | CS | withdrawn `CS` (Serbia and Montenegro, CSXX) | ISO, Remark part 1: "Former code element CS was reused for Serbia and Montenegro" |
| FXFR | France, Metropolitan | FX | nothing | exceptionally reserved; period 1993/1997 |
| GEHH | Gilbert and Ellice Islands | GE | active `GE` (Georgia) | ISO: divided into Kiribati (KI) and Tuvalu (TV); GE "reused and reassigned to Georgia" |
| PUUM | United States Miscellaneous Pacific Islands | PU | nothing | now part of UM |

The earlier version of this page, from a Wikipedia lead, called GEHH "Gilbert
Islands" with successor Kiribati only. ISO's page names the Gilbert and
Ellice Islands, divided into Kiribati and Tuvalu.

## What modelling the missing entries needs

**Reused alpha-2 codes (BQ, GE).** An active and a withdrawn entry may share
an alpha-2: `AI` and `SK` do. The validator checks uniqueness within each
section (`tools/validate.py`, `layer_business`), so BQAQ and GEHH fit the
schema. Every read by alpha-2 prefers the active entry
(`docs/QUERIES-DECISIONS.md`, "Why alpha-2 collisions resolve to the active
entry"), so `is_active_on("GE", "1977-01-01")` answers for Georgia.

**A name change under the same alpha-2 (BY).** ISO lists Byelorussian SSR in
ISO 3166-3 because the name and alpha-3 changed, though BY stayed. Whether
such an entry belongs in the withdrawn list is a decision, not a data fix.
ISO's SUHH page also says BY and UA "were separately coded in ISO 3166 already
before the USSR was split", which contradicts the reason BY and UA are
quarantined in `tools/build_introduced_snapshot.py` ("code cannot be in 1974
edition"). It gives no date, so `introduced` stays null for both.

**Two withdrawn rows with one alpha-2 (CS).** CSHH (Czechoslovakia) and CSXX
(Serbia and Montenegro) both carry `CS`. The registry holds only CSXX, now
dated 2003-07-23 by Newsletter V-8. Adding CSHH breaks three things:
`tools/validate.py` rejects a duplicate alpha-2 within `withdrawn`;
`is_active_on` takes the first withdrawn row with the code
(`wrappers/python/iso3166/derived.py`); and `YU`'s `replaced_by: ["CS"]` would
no longer name one entry. The four-letter ISO 3166-3 code is the natural key.
That is a schema change, which this page does not make.

**The effect on `is_active_on`.** A withdrawn row with no `introduced` answers
True from 1974-01-01 to its `withdrawal_date`. For CS this no longer holds:
since `introduced` is 2003-07-23, `is_active_on("CS", "1991-06-01")` is False.
That is the right answer for Serbia and Montenegro; a 1991 `CS` meant
Czechoslovakia, which the registry does not hold. FXFR would need its 1993
start.

## Page hashes

| File | sha256 | Against `SHA256SUMS` |
|------|--------|----------------------|
| obp-3166-3/AIDJ.html | `9261b3ff13644d5791afa32630d04ca0fe81fb53bc82529c8d4b102460fcbab4` | verified |
| obp-reserved/AN.html | `29854ca6b6b9723338cbbea4143290b635a8a1f6fb705418b026d1bce332c760` | verified |
| obp-3166-3/BQAQ.html | `ee4e1584f0a395411562b2e1b8fd65900bb1b419ff3f2241f456a5109cac6b38` | matches (regenerated 2026-11-25) |
| obp-reserved/BU.html | `ba4c6b9b1cdd5a1835cf6ec94e467994018bc6e6e736c92ee6b70f1e468c4fb4` | verified |
| obp-3166-3/BYAA.html | `70d24541a6072a82db8b2289e182d269ab7c91acde81732ae05b9935b8110f59` | matches (regenerated 2026-11-25) |
| obp-3166-3/CSHH.html | `59901673f9be69922c240c9ca8ef874a14e301831110229226fe7bbb97d84087` | matches (regenerated 2026-11-25) |
| obp-reserved/CS.html | `9e3f94be51d74dab1967087034eeb546606bccc18cedaa64a7991e3258b0fb75` | verified |
| obp-3166-3/CTKI.html | `1f9d43d95d75b0261815622c129ff609c4bd36549e573250dfde530a7a3cc1e2` | verified |
| obp-3166-3/DDDE.html | `390b3c108c629b1b2c3e251aadcdded04571eaa3dd4cfd18140b01bada886e2a` | verified |
| obp-3166-3/DYBJ.html | `3e44dbb7e7254810dc7ef5e075c490d8e0a83eef2bf88dbde53283209e47426c` | verified |
| obp-3166-3/FQHH.html | `15ccbb7d6471e60c7a0f4b1abec3befbb3090e5d7b048ae7549cd9bf20f168f0` | verified |
| obp-reserved/FX.html | `ff754e53e7305605adb43db9522111f179632a0d01fac2436b165aa01aed20c8` | verified |
| obp-3166-3/GEHH.html | `34d6540865ab7b584d67015d1869c07c159c13e16d305c05b8282a63ef13ad9b` | matches (regenerated 2026-11-25) |
| obp-3166-3/HVBF.html | `58d4ab815ad99a6e1e6b1fa97d2df74d3b23eb970d86e3e0dcfe5a2817fc0738` | verified |
| obp-3166-3/JTUM.html | `a4166460ee8e19ea513c5b87634a3e73a146f1d4fac6a4dbb9f7d747e9d7630a` | verified |
| obp-3166-3/MIUM.html | `2700a9e63e51065fd9776e9235624de35e89502428df1ac96860b21dc79ed835` | verified |
| obp-3166-3/NHVU.html | `14fb4bc258116c705ad03f90e00774e30901ba1f26d6632beb6c5dd48513d914` | verified |
| obp-3166-3/NQAQ.html | `582bff52374bddc4beaef027ecb0a214414732bcee661ed9a27a0099eb4e1661` | verified |
| obp-reserved/NT.html | `99efe31449b5dd28560126f7abcad6b392694153366433a2f022786bbb49400e` | verified |
| obp-3166-3/PCHH.html | `a7e9de21ac0c75b8a17b13887e77794e9a617f80eb9ca1f757e7a409e4c75095` | verified |
| obp-3166-3/PUUM.html | `f625ed788919e121aa94ba75e0123adc2fd93352cfe15e3f27bd7f1f160c99ca` | matches (regenerated 2026-11-25) |
| obp-3166-3/PZPA.html | `43601037248c29413a26efa22c0576f20aead903f639a243611114346052edf7` | verified |
| obp-3166-3/RHZW.html | `4343f63dd60cbb7a428485004ab4fbd31230d7b56770c7a3e50ce9afe7389fba` | verified |
| obp-3166-3/SKIN.html | `c479ebc7c6755520f6aea589ea9d850518bb8dea7706184f5262650d77c08c9f` | verified |
| obp-reserved/SU.html | `c41b032e412401efef061b4a56e530ec05abf5267aad8bd73bc714fa14f55ff3` | verified |
| obp-reserved/TP.html | `e8ff2aa86b34e0fa0e2f8d0d9e6a82f03d02f6f48395b6ff030ca3d1136aa489` | verified |
| obp-3166-3/VDVN.html | `650f2ea64bdc36beff5f2b417495f894d789ce646d8d94ffed6003bb6462117f` | verified |
| obp-3166-3/WKUM.html | `bf7a9e2c21a2b0a923e2b5b58ed6ee96f0695173cbdea29e493085272cfd2c63` | verified |
| obp-3166-3/YDYE.html | `238621d66366b5a955482aeb3a9282f4c16cf1045bdea665abcf73c0d9ee1574` | verified |
| obp-reserved/YU.html | `a48225f5f2c765351288d4e38f587a340bf4ff6d5ffd7e277ed2515f0fe1bd18` | verified |
| obp-reserved/ZR.html | `5ff9cfe1780912c21c5ad464e7cd5816c6536e0ab864b7dee76e1273bd7b68bf` | verified |
