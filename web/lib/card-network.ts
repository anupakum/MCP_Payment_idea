export type CardNetwork =
  | 'visa'
  | 'mastercard'
  | 'amex'
  | 'discover'
  | 'jcb'
  | 'diners'
  | 'unionpay'
  | 'maestro'
  | 'unknown'

/**
 * Identify card network by BIN (first digits of card number).
 * Accepts either a full card number or a BIN (string/number).
 */
export function identifyCardNetwork(input: string | number): CardNetwork {
  const s = String(input || '').replace(/\D/g, '') // keep digits only
  if (!s) return 'unknown'

  // Extract prefixes of various lengths (safe even if input shorter)
  const p1 = s.slice(0, 1)
  const p2 = s.slice(0, 2)
  const p3 = s.slice(0, 3)
  const p4 = s.slice(0, 4)
  const p6 = s.slice(0, 6)

  const int = (str: string) => (str ? parseInt(str, 10) : NaN)

  // American Express
  if (p2 === '34' || p2 === '37') return 'amex'

  // Visa (starts with 4)
  if (p1 === '4') return 'visa'

  // MasterCard: 51-55 (first 2) OR 2221-2720 (first 4), checked using 6-digit ranges
  const six = int(p6)
  if (!isNaN(six)) {
    if (six >= 510000 && six <= 559999) return 'mastercard'
    if (six >= 222100 && six <= 272099) return 'mastercard'
  } else {
    const two = int(p2)
    const four = int(p4)
    if (!isNaN(two) && two >= 51 && two <= 55) return 'mastercard'
    if (!isNaN(four) && four >= 2221 && four <= 2720) return 'mastercard'
  }

  // Discover: 6011, 622126-622925, 644-649, 65
  if (p4 === '6011') return 'discover'
  const three = int(p3)
  if (!isNaN(three) && three >= 644 && three <= 649) return 'discover'
  if (p2 === '65') return 'discover'
  if (!isNaN(six) && six >= 622126 && six <= 622925) return 'discover'

  // JCB: 3528-3589 (first 4)
  const fourInt = int(p4)
  if (!isNaN(fourInt) && fourInt >= 3528 && fourInt <= 3589) return 'jcb'

  // Diners Club: 300-305, 36, 38-39
  if (!isNaN(three) && three >= 300 && three <= 305) return 'diners'
  if (p2 === '36') return 'diners'
  if (p2 === '38' || p2 === '39') return 'diners'

  // UnionPay: common starting 62 or 81
  if (p2 === '62' || p2 === '81') return 'unionpay'

  // Maestro: common prefixes (non-exhaustive): 5018, 5020, 5038, 6304, 6759, 6761, 6762, 6763
  const maestroPrefixes = ['5018', '5020', '5038', '6304', '6759', '6761', '6762', '6763']
  if (maestroPrefixes.includes(p4) || maestroPrefixes.includes(p6)) return 'maestro'

  return 'unknown'
}
