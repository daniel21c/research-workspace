"""Regression checks for actual dangerous partial-number parses found in audit."""
from address_rules import parse_addr
def test():
 def qs(a):return [c['query'] for c in parse_addr(a)]
 assert '서울특별시 구로구 구로 1' not in qs('서울 구로구 구로1동 구일우성아파트 206동102호')
 assert '서울특별시 중구 명동 13' not in qs('서울특별시 중구 명동13길 18')
 assert '서울특별시 중구 명동13길 18' in qs('서울특별시 중구 명동13길 18')
 assert qs('서울특별시 강남구 테헤란로 123-4')[0]=='서울특별시 강남구 테헤란로 123-4'
 assert not qs('서울특별시 강남구 역삼동')
 assert not qs('서울 도봉구 창4동 동아청솔아파트 109동 104호')
 assert '서울특별시 종로구 성균관로4길 21' in qs('서울특별시 종로구 성균관로 4길 21')
 assert any(c.get('san') for c in parse_addr('서울특별시 은평구 진관동 산 3-1'))
 print('8 regression checks passed')
if __name__=='__main__':test()
