// 全站货币统一：DE=EUR, UK=GBP, JP=JPY, CA=CAD, 其他=USD
export function getMarketCurrency(market?: string) {
  switch ((market || 'US').toUpperCase()) {
    case 'DE':
      return { code: 'EUR', symbol: '€' };
    case 'UK':
      return { code: 'GBP', symbol: '£' };
    case 'JP':
      return { code: 'JPY', symbol: '¥' };
    case 'CA':
      return { code: 'CAD', symbol: 'C$' };
    default:
      return { code: 'USD', symbol: '$' };
  }
}

export function formatMoney(amount: number, market?: string, fractionDigits = 2) {
  const { symbol } = getMarketCurrency(market);
  return `${symbol}${amount.toLocaleString(undefined, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })}`;
}
