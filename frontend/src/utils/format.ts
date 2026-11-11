export const number=(n:number|undefined,d=2)=>n===undefined?'—':n.toLocaleString('zh-CN',{maximumFractionDigits:d,minimumFractionDigits:d});export const percent=(n:number|undefined)=>n===undefined?'—':number(n*100,1)+'%';export const time=(s:string)=>new Date(s).toLocaleString('zh-CN',{hour12:false});
export const probability=(n:number)=>n<.000001?n.toExponential(2):number(n,6);
