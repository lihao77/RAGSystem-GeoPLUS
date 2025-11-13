// 广西省的地理轮廓数据
// 简化版的广西省边界坐标点
// 坐标系统：经度、纬度（WGS84）

export const guangxiOutline = [
  // 西部边界（与云南、贵州接壤）
  { lon: 104.5, lat: 24.5 },
  { lon: 105.2, lat: 25.0 },
  { lon: 106.0, lat: 25.8 },
  { lon: 106.5, lat: 26.3 },
  
  // 北部边界（与贵州、湖南接壤）
  { lon: 107.5, lat: 26.4 },
  { lon: 108.5, lat: 26.3 },
  { lon: 109.5, lat: 26.2 },
  { lon: 110.5, lat: 26.0 },
  { lon: 111.5, lat: 25.8 },
  
  // 东部边界（与广东接壤）
  { lon: 112.0, lat: 25.0 },
  { lon: 111.8, lat: 24.0 },
  { lon: 111.5, lat: 23.0 },
  { lon: 110.8, lat: 22.0 },
  
  // 南部边界（与越南接壤和北部湾）
  { lon: 109.5, lat: 21.5 },
  { lon: 108.5, lat: 21.3 },
  { lon: 107.5, lat: 21.5 },
  { lon: 106.5, lat: 22.0 },
  
  // 西南部边界（与越南接壤）
  { lon: 105.5, lat: 22.5 },
  { lon: 105.0, lat: 23.0 },
  { lon: 104.8, lat: 23.5 },
  { lon: 104.5, lat: 24.0 }
];

// 广西主要城市坐标
export const guangxiCities = [
  { name: '南宁', lon: 108.320004, lat: 22.82402 },
  { name: '桂林', lon: 110.299121, lat: 25.274215 },
  { name: '柳州', lon: 109.411703, lat: 24.314617 },
  { name: '北海', lon: 109.119254, lat: 21.473343 },
  { name: '玉林', lon: 110.18122, lat: 22.654032 },
  { name: '梧州', lon: 111.297604, lat: 23.474803 },
  { name: '贵港', lon: 109.602146, lat: 23.0936 },
  { name: '钦州', lon: 108.624175, lat: 21.967127 },
  { name: '百色', lon: 106.618201, lat: 23.902333 },
  { name: '河池', lon: 108.062105, lat: 24.695899 },
  { name: '来宾', lon: 109.229772, lat: 23.733766 },
  { name: '贺州', lon: 111.552056, lat: 24.414141 },
  { name: '防城港', lon: 108.345478, lat: 21.614631 },
  { name: '崇左', lon: 107.353926, lat: 22.404108 }
];

// 广西主要河流
export const guangxiRivers = [
  // 珠江水系
  { name: '西江', points: [
    { lon: 107.5, lat: 24.8 },
    { lon: 108.5, lat: 24.2 },
    { lon: 109.5, lat: 23.5 },
    { lon: 110.5, lat: 23.2 },
    { lon: 111.3, lat: 23.4 }
  ]},
  { name: '柳江', points: [
    { lon: 109.0, lat: 25.5 },
    { lon: 109.3, lat: 24.8 },
    { lon: 109.4, lat: 24.3 }
  ]},
  { name: '桂江', points: [
    { lon: 110.3, lat: 25.8 },
    { lon: 110.4, lat: 25.2 },
    { lon: 110.5, lat: 24.5 },
    { lon: 110.8, lat: 23.8 }
  ]},
  { name: '郁江', points: [
    { lon: 107.0, lat: 23.0 },
    { lon: 108.0, lat: 22.8 },
    { lon: 109.0, lat: 23.0 },
    { lon: 109.5, lat: 23.5 }
  ]}
];

// 广西地形特征
export const guangxiTerrain = {
  // 广西地形以喀斯特地貌为主
  karst: [
    { center: { lon: 108.8, lat: 24.8 }, radius: 0.8 }, // 桂林喀斯特
    { center: { lon: 107.2, lat: 24.5 }, radius: 0.7 }, // 河池喀斯特
    { center: { lon: 106.8, lat: 23.5 }, radius: 0.6 }  // 百色喀斯特
  ],
  // 主要山脉
  mountains: [
    { name: '大瑶山', lon: 110.5, lat: 24.2 },
    { name: '猫儿山', lon: 110.0, lat: 25.8 },
    { name: '大明山', lon: 108.8, lat: 23.5 },
    { name: '十万大山', lon: 107.5, lat: 22.0 }
  ],
  // 主要平原
  plains: [
    { name: '桂中平原', lon: 109.5, lat: 23.5 },
    { name: '右江河谷平原', lon: 106.8, lat: 23.2 },
    { name: '南宁盆地', lon: 108.3, lat: 22.8 }
  ]
};