# Mini-Disassembler fuer 65816 (reicht zum Lesen kurzer Stellen). Aufruf: dis65816.py rom.smc SNES-Adresse Laenge [m] [x]
import sys
OPS={}
def d(op,mn,mode): OPS[op]=(mn,mode)
tbl="""00 BRK imm8|01 ORA dpxi|02 COP imm8|03 ORA sr|04 TSB dp|05 ORA dp|06 ASL dp|07 ORA dpil|08 PHP imp|09 ORA immm|0A ASL imp|0B PHD imp|0C TSB abs|0D ORA abs|0E ASL abs|0F ORA long
10 BPL rel|11 ORA dpiy|12 ORA dpi|13 ORA sriy|14 TRB dp|15 ORA dpx|16 ASL dpx|17 ORA dpily|18 CLC imp|19 ORA absy|1A INC imp|1B TCS imp|1C TRB abs|1D ORA absx|1E ASL absx|1F ORA longx
20 JSR abs|21 AND dpxi|22 JSL long|23 AND sr|24 BIT dp|25 AND dp|26 ROL dp|27 AND dpil|28 PLP imp|29 AND immm|2A ROL imp|2B PLD imp|2C BIT abs|2D AND abs|2E ROL abs|2F AND long
30 BMI rel|31 AND dpiy|32 AND dpi|33 AND sriy|34 BIT dpx|35 AND dpx|36 ROL dpx|37 AND dpily|38 SEC imp|39 AND absy|3A DEC imp|3B TSC imp|3C BIT absx|3D AND absx|3E ROL absx|3F AND longx
40 RTI imp|41 EOR dpxi|42 WDM imm8|43 EOR sr|44 MVP mv|45 EOR dp|46 LSR dp|47 EOR dpil|48 PHA imp|49 EOR immm|4A LSR imp|4B PHK imp|4C JMP abs|4D EOR abs|4E LSR abs|4F EOR long
50 BVC rel|51 EOR dpiy|52 EOR dpi|53 EOR sriy|54 MVN mv|55 EOR dpx|56 LSR dpx|57 EOR dpily|58 CLI imp|59 EOR absy|5A PHY imp|5B TCD imp|5C JML long|5D EOR absx|5E LSR absx|5F EOR longx
60 RTS imp|61 ADC dpxi|62 PER rel16|63 ADC sr|64 STZ dp|65 ADC dp|66 ROR dp|67 ADC dpil|68 PLA imp|69 ADC immm|6A ROR imp|6B RTL imp|6C JMP absi|6D ADC abs|6E ROR abs|6F ADC long
70 BVS rel|71 ADC dpiy|72 ADC dpi|73 ADC sriy|74 STZ dpx|75 ADC dpx|76 ROR dpx|77 ADC dpily|78 SEI imp|79 ADC absy|7A PLY imp|7B TDC imp|7C JMP absxi|7D ADC absx|7E ROR absx|7F ADC longx
80 BRA rel|81 STA dpxi|82 BRL rel16|83 STA sr|84 STY dp|85 STA dp|86 STX dp|87 STA dpil|88 DEY imp|89 BIT immm|8A TXA imp|8B PHB imp|8C STY abs|8D STA abs|8E STX abs|8F STA long
90 BCC rel|91 STA dpiy|92 STA dpi|93 STA sriy|94 STY dpx|95 STA dpx|96 STX dpy|97 STA dpily|98 TYA imp|99 STA absy|9A TXS imp|9B TXY imp|9C STZ abs|9D STA absx|9E STZ absx|9F STA longx
A0 LDY immx|A1 LDA dpxi|A2 LDX immx|A3 LDA sr|A4 LDY dp|A5 LDA dp|A6 LDX dp|A7 LDA dpil|A8 TAY imp|A9 LDA immm|AA TAX imp|AB PLB imp|AC LDY abs|AD LDA abs|AE LDX abs|AF LDA long
B0 BCS rel|B1 LDA dpiy|B2 LDA dpi|B3 LDA sriy|B4 LDY dpx|B5 LDA dpx|B6 LDX dpy|B7 LDA dpily|B8 CLV imp|B9 LDA absy|BA TSX imp|BB TYX imp|BC LDY absx|BD LDA absx|BE LDX absy|BF LDA longx
C0 CPY immx|C1 CMP dpxi|C2 REP imm8|C3 CMP sr|C4 CPY dp|C5 CMP dp|C6 DEC dp|C7 CMP dpil|C8 INY imp|C9 CMP immm|CA DEX imp|CB WAI imp|CC CPY abs|CD CMP abs|CE DEC abs|CF CMP long
D0 BNE rel|D1 CMP dpiy|D2 CMP dpi|D3 CMP sriy|D4 PEI dp|D5 CMP dpx|D6 DEC dpx|D7 CMP dpily|D8 CLD imp|D9 CMP absy|DA PHX imp|DB STP imp|DC JML absil|DD CMP absx|DE DEC absx|DF CMP longx
E0 CPX immx|E1 SBC dpxi|E2 SEP imm8|E3 SBC sr|E4 CPX dp|E5 SBC dp|E6 INC dp|E7 SBC dpil|E8 INX imp|E9 SBC immm|EA NOP imp|EB XBA imp|EC CPX abs|ED SBC abs|EE INC abs|EF SBC long
F0 BEQ rel|F1 SBC dpiy|F2 SBC dpi|F3 SBC sriy|F4 PEA abs|F5 SBC dpx|F6 INC dpx|F7 SBC dpily|F8 SED imp|F9 SBC absy|FA PLX imp|FB XCE imp|FC JSR absxi|FD SBC absx|FE INC absx|FF SBC longx"""
for line in tbl.split("\n"):
    for e in line.split("|"):
        o,mn,mo=e.split(); d(int(o,16),mn,mo)
SZ={'imp':0,'imm8':1,'dp':1,'dpx':1,'dpy':1,'dpi':1,'dpxi':1,'dpiy':1,'dpil':1,'dpily':1,'sr':1,'sriy':1,'rel':1,'abs':2,'absx':2,'absy':2,'absi':2,'absxi':2,'absil':2,'rel16':2,'mv':2,'long':3,'longx':3}
FMT={'imp':'','imm8':'#${:02X}','immm':'#${}','immx':'#${}','dp':'${:02X}','dpx':'${:02X},X','dpy':'${:02X},Y','dpi':'(${:02X})','dpxi':'(${:02X},X)','dpiy':'(${:02X}),Y','dpil':'[${:02X}]','dpily':'[${:02X}],Y','sr':'${:02X},S','sriy':'(${:02X},S),Y','abs':'${:04X}','absx':'${:04X},X','absy':'${:04X},Y','absi':'(${:04X})','absxi':'(${:04X},X)','absil':'[${:04X}]','long':'${:06X}','longx':'${:06X},X'}
def fo(a): return (a & 0x3FFFFF) if (a>>16)&0x40 or (a>>16)>=0xC0 else (((a>>16)&0x3F)<<16)|(a&0xFFFF)
def dis(rom,a,n,m8=False,x8=False):
    end=a+n; out=[]
    while a<end:
        o=fo(a); op=rom[o]; mn,mo=OPS[op]
        if mo=='immm': s=1 if m8 else 2
        elif mo=='immx': s=1 if x8 else 2
        else: s=SZ[mo]
        b=rom[o+1:o+1+s]; v=int.from_bytes(b,'little') if s else 0
        if mo in('immm','immx'): arg='#$%0*X'%(2*s,v)
        elif mo=='rel': t=(a+2+(v-256 if v>127 else v))&0xFFFF; arg='$%04X'%t
        elif mo=='rel16': t=(a+3+(v-65536 if v>32767 else v))&0xFFFF; arg='$%04X'%t
        elif mo=='mv': arg='$%02X,$%02X'%(b[0],b[1])
        else: arg=FMT[mo].format(v) if s else ''
        if mn=='REP': m8 = m8 and not (v&0x20); x8 = x8 and not (v&0x10)
        if mn=='SEP': m8 = m8 or bool(v&0x20); x8 = x8 or bool(v&0x10)
        out.append('%02X:%04X  %-12s %s %s'%(a>>16,a&0xFFFF,rom[o:o+1+s].hex(' '),mn,arg)); a+=1+s
    return out
if __name__=='__main__':
    rom=open(sys.argv[1],'rb').read(); rom=rom[len(rom)%1024:]
    a=int(sys.argv[2],16); n=int(sys.argv[3]); m8=len(sys.argv)>4 and sys.argv[4]=='1'; x8=len(sys.argv)>5 and sys.argv[5]=='1'
    print("\n".join(dis(rom,a,n,m8,x8)))
