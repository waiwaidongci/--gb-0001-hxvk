export const Roles={admin:'实验负责人',analyst:'数据分析师',viewer:'业务观察员'} as const;
export const RunStatus={queued:'排队中',running:'分析中',completed:'已完成',failed:'失败'} as const;
export const Outcomes={ship:'同意放量',hold:'继续观察',reject:'暂缓上线'} as const;
