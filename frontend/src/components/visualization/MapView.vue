<template>
    <div class="map-container">
        <div id="mapContainer" ref="mapContainer" class="map-view"></div>
        
        <!-- 左侧：状态详情区域 -->
        <div v-if="selectedStates.length > 0" class="states-container" :class="{ collapsed: statesCollapsed }">
            <div class="states-scroll-content">
                <div v-for="state in selectedStates" :key="state.id" class="state-detail-card">
                    <button class="state-close-btn" @click="closeStateDetail(state)">×</button>
                    <StateDetails :state="state" @select-entity="handleEntitySelect" />
                </div>
            </div>
        </div>

        <!-- 右上：实体详情面板 -->
        <div v-if="selectedEntity" class="entity-details" :class="{ collapsed: entityCollapsed }">
            <div class="panel-header">
                <h3 class="panel-title">{{ selectedEntity.name || selectedEntity.id }}</h3>
                <div class="header-actions">
                    <button class="close-btn" @click="closeDetails">✕</button>
                </div>
            </div>
            
            <div class="entity-scroll-content" v-show="!entityCollapsed">
                <div class="entity-type">类型: {{ selectedEntity.type }}</div>

                <!-- 相关状态树 -->
                <StateTree 
                    v-if="stateTreeData && stateTreeData.rootStates && stateTreeData.rootStates.length > 0" 
                    :state-tree-data="stateTreeData" 
                    :selected-states="selectedStates" 
                    @select-state="selectState" 
                />

                <!-- 相关事件 -->
                <div v-if="relatedEvents.length > 0" class="related-section">
                    <h4>相关事件</h4>
                    <div v-for="event in relatedEvents" :key="event.id" class="event-item" @click="selectEntity(event)">
                        <div class="event-name">{{ event.name || event.id }}</div>
                        <div class="event-time" v-if="event.time">{{ formatTime(event.time) }}</div>
                    </div>
                </div>

                <!-- 相关设施 -->
                <div v-if="relatedFacilities.length > 0" class="related-section">
                    <h4>相关设施</h4>
                    <div v-for="facility in relatedFacilities" :key="facility.id" class="facility-item"
                        @click="selectEntity(facility)">
                        <div class="facility-name">{{ facility.name || facility.id }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import XYZ from 'ol/source/XYZ';
import { Feature } from 'ol';
import { Point, LineString } from 'ol/geom';
import { fromLonLat, toLonLat } from 'ol/proj';
import { Style, Circle, Fill, Stroke, Text } from 'ol/style';
import WKT from 'ol/format/WKT';
import { getCenter } from 'ol/extent';
import StateDetails from './StateDetails.vue';
import StateTree from './StateTree.vue';
import { guangxiOutline } from './utils/guangxi_outline.js';
import { entityService } from '../../api';

import 'ol/ol.css';

// 响应式状态
const mapContainer = ref(null);
const map = ref(null);
const vectorSource = ref(null);
const vectorLayer = ref(null);
const graphData = ref({ nodes: [], links: [] });
const selectedEntity = ref(null);
const selectType = ref(null);

// 面板折叠状态
const statesCollapsed = ref(false);
const entityCollapsed = ref(false);

// 接收父组件传递的属性
const props = defineProps({
    // 当前选中的实体
    entityId: {
        type: String,
        default: null
    },
});
// 监听实体ID变化
// watch(() => props.entityId, (newId) => {
//     if (newId) {
//         fetchEntityById(newId);
//     } else {
//         closeDetails();
//     }
// });
const selectedStates = ref([]);
const relatedStates = ref([]);
const stateTreeData = ref(null); // 存储状态树数据
const relatedEvents = ref([]);
const relatedFacilities = ref([]);
const loading = ref(true);
const error = ref(null);


// 初始化 OpenLayers
onMounted(() => {
    // 创建矢量数据源和图层
    vectorSource.value = new VectorSource();
    vectorLayer.value = new VectorLayer({
        source: vectorSource.value,
        style: styleFunction,
        // 启用渲染顺序功能，确保按 zIndex 排序
        renderOrder: (feature1, feature2) => {
            const style1 = feature1.getStyle();
            const style2 = feature2.getStyle();
            
            // 获取 zIndex，如果是数组取第一个样式的 zIndex
            let zIndex1 = 0;
            let zIndex2 = 0;
            
            if (Array.isArray(style1) && style1.length > 0) {
                zIndex1 = style1[0].getZIndex() || 0;
            } else if (style1) {
                zIndex1 = style1.getZIndex() || 0;
            }
            
            if (Array.isArray(style2) && style2.length > 0) {
                zIndex2 = style2[0].getZIndex() || 0;
            } else if (style2) {
                zIndex2 = style2.getZIndex() || 0;
            }
            
            // 返回排序值：zIndex 小的在前（下层），zIndex 大的在后（上层）
            return zIndex1 - zIndex2;
        }
    });

    // 初始化地图
    map.value = new Map({
        target: mapContainer.value,
        layers: [
            new TileLayer({
                source: new XYZ({
                    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    // 可选的其他 ArcGIS 底图服务:
                    // World_Street_Map: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}'
                    // World_Topo_Map: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
                    // NatGeo_World_Map: 'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}'
                    attributions: 'Tiles © <a href="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer">ArcGIS</a>',
                    maxZoom: 19
                })
            }),
            vectorLayer.value
        ],
        view: new View({
            center: fromLonLat([108.3, 23.5]), // 广西中心位置
            zoom: 7,
            minZoom: 6,
            maxZoom: 18
        })
    });

    // 添加点击事件处理
    map.value.on('click', onMapClick);

    // 添加鼠标移动事件，改变光标样式
    map.value.on('pointermove', (evt) => {
        const pixel = map.value.getEventPixel(evt.originalEvent);
        const hit = map.value.hasFeatureAtPixel(pixel);
        map.value.getTarget().style.cursor = hit ? 'pointer' : '';
    });

    // 加载知识图谱数据
    loadKnowledgeGraphData();

    // 添加广西省边界
    // addGuangxiOutline();
});

// 在组件销毁时清理资源
onUnmounted(() => {
    if (map.value) {
        map.value.setTarget(null);
    }
});

// 根据地名推断行政层级（数字越大，层级越低，显示在越上层）
const getAdministrativeLevel = (node) => {
    const name = node.name;

    if (!name) return 0;
    
    // 定义行政层级关键词
    const levelKeywords = {
        1: ['省', '自治区', '直辖市', '特别行政区'], // 省级
        2: ['市', '地区', '州', '盟'],              // 地级市
        3: ['区', '县', '县级市', '旗'],            // 县级
        4: ['镇', '乡', '街道', '苏木'],            // 乡镇级
        5: ['村', '社区', '嘎查']                   // 村级
    };

    if (node.type === '地点') {
        const nodeId = node.id || '';
        // 特殊处理一些常见地点类型
        // 解析地理ID以确定层级关系
        // 例如: L-450100 (市级), L-450102 (区县级), L-450102>某镇 (镇级), L-450102>某镇>某村 (村级)
        const geoIdParts = nodeId.split('>');
        if (geoIdParts.length === 1) {
            // 只有一级，可能是省级、市级或县级，根据ID结尾判断以0000结尾为省级，以00结尾为市级，否则为县级
            const id = geoIdParts[0];
            if (id.match(/0000$/)) {
                return 1; // 省级
            } else if (id.match(/00$/)) {
                return 2; // 市级
            } else {
                return 3; // 县级
            }
        } else if (geoIdParts.length === 2) {
            return 4; // 镇级
        } else if (geoIdParts.length >= 3) {
            return 5; // 村级
        }
    }

    // 从高到低检查层级
    for (let level = 1; level <= 5; level++) {
        for (let keyword of levelKeywords[level]) {
            if (name.includes(keyword)) {
                return level;
            }
        }
    }
    
    // 如果没有匹配，根据几何类型推断
    return 5; // 默认层级
};

// 根据行政层级计算 zIndex（层级越高，zIndex 越低，显示在下层）
const getZIndexByLevel = (level) => {
    // 基础 zIndex
    const baseZIndex = 100;
    // 层级1（省）: zIndex = 100
    // 层级2（市）: zIndex = 200
    // 层级3（县）: zIndex = 300
    // 层级4（乡镇）: zIndex = 400
    // 层级5（村）: zIndex = 500
    return baseZIndex + (level * 100);
};

// 样式函数
const styleFunction = (feature) => {
    const type = feature.get('type');
    const name = feature.get('name');
    const geometryType = feature.getGeometry().getType();
    const adminLevel = feature.get('adminLevel') || 0;

    // 如果是关系线
    if (geometryType === 'LineString') {
        const relationType = feature.get('relationType');
        let strokeColor = '#aaaaaa';
        let lineDash = null;

        if (relationType === 'hasState') {
            strokeColor = '#ffaa00';
        } else if (relationType === 'nextState') {
            strokeColor = '#00aaff';
        } else if (relationType === 'contain') {
            strokeColor = '#aa00ff';
            lineDash = [10, 10];
        }

        return new Style({
            stroke: new Stroke({
                color: strokeColor,
                width: 2,
                lineDash: lineDash
            }),
            zIndex: 50 // 关系线在最底层
        });
    }

    // 如果是实体点或多边形
    let fillColor = 'rgba(128, 128, 128, 0.5)';
    let strokeColor = '#ffffff';
    let radius = 8;

    if (type === '地点') {
        // 根据行政层级调整透明度
        // 层级越高（数字越小），透明度越低
        const opacity = adminLevel === 0 ? 0.6 : Math.max(0.2, 0.8 - (adminLevel * 0.1));
        fillColor = `rgba(255, 0, 0, ${opacity})`;
        radius = 10;
    } else if (type === '设施') {
        fillColor = 'rgba(0, 255, 0, 0.6)';
        radius = 8;
    } else if (type === 'State') {
        fillColor = 'rgba(0, 0, 255, 0.6)';
        radius = 8;
    } else if (type === '事件') {
        fillColor = 'rgba(255, 255, 0, 0.6)';
        radius = 10;
    }

    const styles = [];

    // 如果是多边形或多点，使用面样式
    if (geometryType === 'Polygon' || geometryType === 'MultiPolygon') {
        styles.push(new Style({
            fill: new Fill({
                color: fillColor
            }),
            stroke: new Stroke({
                color: strokeColor,
                width: 2
            })
        }));
    } else {
        // 点样式
        styles.push(new Style({
            image: new Circle({
                radius: radius,
                fill: new Fill({
                    color: fillColor
                }),
                stroke: new Stroke({
                    color: strokeColor,
                    width: 2
                })
            })
        }));
    }

    // 添加标签
    if (name) {
        styles.push(new Style({
            text: new Text({
                text: name,
                font: '12px sans-serif',
                fill: new Fill({
                    color: '#000'
                }),
                stroke: new Stroke({
                    color: '#fff',
                    width: 3
                }),
                offsetY: -15
            })
        }));
    }

    return styles;
};

// 转换数据为 OpenLayers 所需格式
const convertDataToCesiumFormat = (data) => {
    const nodes = data.entities.map(entity => {
        return {
            id: entity.id,
            name: entity.name || entity.value || entity.type || entity.id,
            type: entity.type,
            longitude: entity.longitude || 0,
            latitude: entity.latitude || 0,
            time: entity.time,
            geo: entity.geo
        };
    });

    // 过滤掉无效的关系
    const links = data.relationships
        .filter(rel => {
            const sourceExists = nodes.some(node => node.id === rel.source);
            const targetExists = nodes.some(node => node.id === rel.target);
            return sourceExists && targetExists && rel.source && rel.target;
        })
        .map(rel => ({
            source: rel.source,
            target: rel.target,
            type: rel.type,
            entities: rel.entities
        }));

    return { nodes, links };
}
// 加载知识图谱数据
const loadKnowledgeGraphData = async () => {
    try {
        loading.value = true;
        const data = await entityService.getEntityRelationships();
        console.log('知识图谱数据:', data);
        graphData.value = convertDataToCesiumFormat(data);

        // 添加知识图谱实体到Cesium
        addKnowledgeGraphEntities(graphData.value);
    } catch (err) {
        error.value = err.message;
        console.error('获取数据错误:', err);
    } finally {
        loading.value = false;
    }
};

// 添加广西省边界
const addGuangxiOutline = () => {
    if (!map.value || !vectorSource.value) return;

    // 创建广西省边界线坐标
    const coordinates = guangxiOutline.map(point =>
        fromLonLat([point.lon, point.lat])
    );

    // 闭合轮廓
    coordinates.push(coordinates[0]);

    // 创建边界线要素
    const boundaryFeature = new Feature({
        geometry: new LineString(coordinates),
        name: '广西省边界',
        type: 'boundary'
    });

    // 设置边界线样式
    boundaryFeature.setStyle(new Style({
        stroke: new Stroke({
            color: '#87CEEB',
            width: 2,
            lineDash: [10, 10]
        })
    }));

    vectorSource.value.addFeature(boundaryFeature);
};

// 添加知识图谱实体到 OpenLayers
const addKnowledgeGraphEntities = (data) => {
    if (!map.value || !vectorSource.value || !data.nodes.length) return;

    // 清除现有要素（除了边界线）
    const features = vectorSource.value.getFeatures();
    features.forEach(feature => {
        if (feature.get('type') !== 'boundary') {
            vectorSource.value.removeFeature(feature);
        }
    });

    console.log('addKnowledgeGraphEntities', data);

    // WKT 格式解析器
    const wktFormat = new WKT();

    // 添加地点和设施实体
    data.nodes.forEach(node => {
        let feature = null;

        // 优先使用 WKT 格式的地理数据
        if (node.geo) {
            try {
                // 解析 WKT 格式
                feature = wktFormat.readFeature(node.geo, {
                    dataProjection: 'EPSG:4326',
                    featureProjection: 'EPSG:3857'
                });
            } catch (error) {
                console.error('WKT 解析错误:', error, 'WKT:', node.geo);
            }
        }

        // 如果没有 WKT 数据或解析失败，使用经纬度创建点
        if (!feature && node.longitude && node.latitude) {
            feature = new Feature({
                geometry: new Point(fromLonLat([node.longitude, node.latitude]))
            });
        }

        if (feature) {
            // 设置要素属性
            feature.setId(node.id);
            feature.set('id', node.id);
            feature.set('name', node.name);
            feature.set('type', node.type);
            feature.set('time', node.time);
            feature.set('nodeData', node);
            
            // 根据地名判断行政层级
            const adminLevel = getAdministrativeLevel(node);
            feature.set('adminLevel', adminLevel);
            
            // 根据层级计算 zIndex
            const zIndex = getZIndexByLevel(adminLevel);
            
            // 获取当前样式并设置 zIndex
            const currentStyle = styleFunction(feature);
            if (Array.isArray(currentStyle)) {
                currentStyle.forEach(style => style.setZIndex(zIndex));
            } else if (currentStyle) {
                currentStyle.setZIndex(zIndex);
            }
            
            feature.setStyle(currentStyle);

            vectorSource.value.addFeature(feature);
        }
    });

    // 添加实体之间的关系线
    // data.links.forEach(link => {
    //     const sourceNode = data.nodes.find(node => node.id === link.source);
    //     const targetNode = data.nodes.find(node => node.id === link.target);

    //     if (sourceNode && targetNode) {
    //         // 获取源和目标要素的中心点
    //         let sourceCoord = null;
    //         let targetCoord = null;

    //         // 尝试从 WKT 获取中心点
    //         if (sourceNode.geo) {
    //             try {
    //                 const sourceFeature = wktFormat.readFeature(sourceNode.geo, {
    //                     dataProjection: 'EPSG:4326',
    //                     featureProjection: 'EPSG:3857'
    //                 });
    //                 const extent = sourceFeature.getGeometry().getExtent();
    //                 sourceCoord = getCenter(extent);
    //             } catch (error) {
    //                 console.error('获取源节点中心点错误:', error);
    //             }
    //         }

    //         if (targetNode.geo) {
    //             try {
    //                 const targetFeature = wktFormat.readFeature(targetNode.geo, {
    //                     dataProjection: 'EPSG:4326',
    //                     featureProjection: 'EPSG:3857'
    //                 });
    //                 const extent = targetFeature.getGeometry().getExtent();
    //                 targetCoord = getCenter(extent);
    //             } catch (error) {
    //                 console.error('获取目标节点中心点错误:', error);
    //             }
    //         }

    //         // 如果 WKT 失败，使用经纬度
    //         if (!sourceCoord && sourceNode.longitude && sourceNode.latitude) {
    //             sourceCoord = fromLonLat([sourceNode.longitude, sourceNode.latitude]);
    //         }

    //         if (!targetCoord && targetNode.longitude && targetNode.latitude) {
    //             targetCoord = fromLonLat([targetNode.longitude, targetNode.latitude]);
    //         }

    //         // 创建关系线
    //         if (sourceCoord && targetCoord) {
    //             const lineFeature = new Feature({
    //                 geometry: new LineString([sourceCoord, targetCoord]),
    //                 relationType: link.type,
    //                 linkData: link
    //             });

    //             vectorSource.value.addFeature(lineFeature);
    //         }
    //     }
    // });
};

// 地图点击事件处理
const onMapClick = (evt) => {
    const feature = map.value.forEachFeatureAtPixel(evt.pixel, (feature) => {
        return feature;
    });

    if (feature && feature.get('nodeData')) {
        const nodeData = feature.get('nodeData');

        
        // 只发送事件，不在这里执行飞行动作
        // 飞行动作由 updateSelectedEntity 统一处理，避免重复飞行
        emit('select-entity', nodeData);
    }
};
const emit = defineEmits(['select-entity', 'reset-view'])

// 处理从StateDetails组件发出的实体选择事件
const handleEntitySelect = async (entityId) => {
    try {
        // 获取实体详细信息
        const entity = await entityService.getEntityById(entityId);

        // 使用现有的selectEntity函数处理实体选择
        selectEntity(entity);
    } catch (err) {
        console.error('处理实体选择错误:', err);
    }
};

// 选择实体
const updateSelectedEntity = (entity) => {
    if (selectType.value == '事件' && entity.type !== '事件') {
        selectType.value = entity.type;

    // } else if (entity.type === '事件' && entity.longitude && entity.latitude) {
    } else if (entity.type === '事件') {
        selectedEntity.value = entity;
        fetchRelatedFacilities(entity.id);
        fetchEntityStates(entity.id);
        selectType.value = entity.type;
        // flyToLocation();
    }
    if (entity.type === '地点' || entity.type === '设施') {
        selectedEntity.value = entity;
        // 不再清空selectedStates，保留已选择的状态详情
        // selectedStates.value = [];

        fetchEntityStates(entity.id);
        fetchRelatedEvents(entity.id);
        fetchRelatedFacilities(entity.id);

        // 飞向选中的实体
        // 优先尝试使用几何数据
        if (entity.geo) {
            try {
                const wktFormat = new WKT();
                const feature = wktFormat.readFeature(entity.geo, {
                    dataProjection: 'EPSG:4326',
                    featureProjection: 'EPSG:3857'
                });
                const geometry = feature.getGeometry();
                if (geometry.getType() === 'Polygon' || geometry.getType() === 'MultiPolygon') {
                    flyToGeometry(geometry);
                } else if (entity.longitude && entity.latitude) {
                    flyToLocation(entity.longitude, entity.latitude);
                }
            } catch (error) {
                console.error('解析 WKT 失败:', error);
                // 如果解析失败，尝试使用经纬度
                if (entity.longitude && entity.latitude) {
                    flyToLocation(entity.longitude, entity.latitude);
                }
            }
        } else if (entity.longitude && entity.latitude) {
            // 如果没有几何数据，使用经纬度
            flyToLocation(entity.longitude, entity.latitude);
        }
    }
};

const selectEntity = (entity) => {
    selectedEntity.value = entity;
    // 不再清空selectedStates，保留已选择的状态详情
    // selectedStates.value = [];
    relatedEvents.value = [];
    relatedFacilities.value = [];
    relatedStates.value = [];

    emit('select-entity', entity);
};

// 选择状态
const selectState = async (state) => {
    console.log('selectState', state);
    try {
        // 检查状态是否已经被选中
        const existingIndex = selectedStates.value.findIndex(s => s.id === state.id);
        if (existingIndex >= 0) {
            // 如果已经选中，则不做任何操作
            return;
        }
        const stateDetails = await entityService.getStateDetails(state.id);
        // 添加到选中状态数组
        selectedStates.value.push({ ...state, description: stateDetails });
    } catch (err) {
        console.error('获取状态详情错误:', err);
        // 即使出错也添加到数组中
        const existingIndex = selectedStates.value.findIndex(s => s.id === state.id);
        if (existingIndex < 0) {
            selectedStates.value.push(state);
        }
    }
};

// 关闭单个状态详情
const closeStateDetail = (state) => {
    const index = selectedStates.value.findIndex(s => s.id === state.id);
    if (index >= 0) {
        selectedStates.value.splice(index, 1);
    }
};

// 清空所有状态详情
const clearAllStates = () => {
    selectedStates.value = [];
};

// 清空详情面板
const closeDetails = () => {
    selectedEntity.value = null;
    // selectedStates.value = [];
    relatedStates.value = [];
    stateTreeData.value = null;
    relatedEvents.value = [];
    relatedFacilities.value = [];
    addKnowledgeGraphEntities(graphData.value);
    // emit('reset-view');
};

// 飞向指定位置
const flyToLocation = (longitude, latitude) => {
    if (!map.value) return;

    const view = map.value.getView();
    view.animate({
        center: fromLonLat([longitude, latitude]),
        zoom: 11,
        duration: 1000
    });
};

// 飞向指定几何体（用于面数据）
const flyToGeometry = (geometry) => {
    if (!map.value || !geometry) return;

    const view = map.value.getView();
    const extent = geometry.getExtent();
    
    // 使用 fit 方法自动调整视图以适配几何体范围
    view.fit(extent, {
        padding: [50, 450, 50, 400], // 添加边距，避免要素贴边
        duration: 1000,             // 动画持续时间
        maxZoom: 15                 // 限制最大缩放级别，避免放得太大
    });
};

// 显示事件及其发生地点
const loadSelectData = (eventData, Type) => {
    selectedEntity.value = null;
    // selectedStates.value = [];
    relatedStates.value = [];
    relatedEvents.value = [];
    relatedFacilities.value = [];
    const eventData1 = convertDataToCesiumFormat(eventData);
    selectType.value = Type;

    addKnowledgeGraphEntities(eventData1);

    // // 显示事件信息弹窗
    // selectedEntity.value = eventNode;

    // // 获取事件相关的状态和其他信息
    // if (eventNode.id) {
    //     fetchEntityStates(eventNode.id);
    // }
};


// 暴露方法给父组件
defineExpose({
    flyToLocation,
    flyToGeometry,
    updateSelectedEntity,
    loadSelectData,
    selectState
});


// 获取实体的状态链
const fetchEntityStates = async (entityId) => {
    try {
        const data = await entityService.getEntityStates(entityId);
        
        // 保存完整的状态树数据
        stateTreeData.value = data;
        
        // 为了兼容性，同时更新relatedStates
        relatedStates.value = data.states || [];
        
        console.log('状态树数据:', stateTreeData.value);
    } catch (err) {
        console.error('获取状态链错误:', err);
        relatedStates.value = [];
        stateTreeData.value = null;
    }
};

// 获取与实体相关的事件
const fetchRelatedEvents = async (entityId) => {
    try {
        const data = await entityService.getEntityEvents(entityId);
        relatedEvents.value = data;
    } catch (err) {
        console.error('获取相关事件错误:', err);
        relatedEvents.value = [];
    }
};

// 获取与实体相关的设施
const fetchRelatedFacilities = async (entityId) => {
    try {
        const data = await entityService.getEntityFacilities(entityId);
        relatedFacilities.value = data;
    } catch (err) {
        console.error('获取相关设施错误:', err);
        relatedFacilities.value = [];
    }
};

// 格式化时间显示
const formatTime = (timeString) => {
    if (!timeString) return '未知时间';

    // 处理时间范围格式 (2023-10-01至2023-10-10)
    if (timeString.includes('至')) {
        const [start, end] = timeString.split('至');
        return `${formatDate(start)} 至 ${formatDate(end)}`;
    }

    return formatDate(timeString);
};

// 格式化日期
const formatDate = (dateString) => {
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString; // 如果无法解析，返回原始字符串

        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        return dateString;
    }
};

// 获取状态描述
const getStateDescription = (state) => {
    if (!state) return '';

    // 尝试从状态数据中提取描述信息
    // 这里的实现可能需要根据实际数据结构调整
    if (state.description) return state.description;

    // 如果没有直接的描述，尝试从其他属性构建描述
    const props = getStateProperties(state);
    if (Object.keys(props).length > 0) {
        const key = Object.keys(props)[0];
        return `${formatPropertyKey(key)}: ${props[key]}`;
    }

    return '状态详情';
};

// 获取状态属性
const getStateProperties = (state) => {
    if (!state) return {};

    // 过滤掉不需要显示的属性
    const excludeKeys = ['id', 'type', 'time', 'geo', 'entityIds'];
    const properties = {};

    for (const key in state) {
        if (!excludeKeys.includes(key) && state[key]) {
            properties[key] = state[key];
        }
    }

    return properties;
};

// 格式化属性键名
const formatPropertyKey = (key) => {
    // 将驼峰命名转换为空格分隔的词组
    return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
};

</script>

<style scoped>
.map-container {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: linear-gradient(135deg, #f5f7fa 0%, #e8eaf0 100%);
}

.map-view {
    width: 100%;
    height: 100%;
}

/* 统一的实体详情面板样式 */
.entity-details {
    position: absolute;
    top: 20px;
    right: 20px;
    width: 360px;
    max-height: calc(100% - 40px);
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 251, 252, 0.98) 100%);
    color: #333;
    border-radius: 16px;
    padding: 24px;
    overflow-y: auto;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.8);
    z-index: 1000;
    animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(30px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.entity-details h3 {
    margin: 0 0 16px 0;
    font-size: 20px;
    font-weight: 600;
    color: #1a1a1a;
    border-bottom: 2px solid #e3e8ef;
    padding-bottom: 12px;
    line-height: 1.4;
}

.entity-details h4 {
    margin-top: 20px;
    margin-bottom: 12px;
    font-size: 16px;
    font-weight: 600;
    color: #2c3e50;
    display: flex;
    align-items: center;
    gap: 8px;
}

.entity-details h4::before {
    content: '';
    width: 4px;
    height: 16px;
    background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
    border-radius: 2px;
}

.entity-type {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #1890ff;
    background: linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(9, 109, 217, 0.1) 100%);
    padding: 8px 14px;
    border-radius: 20px;
    border: 1px solid rgba(24, 144, 255, 0.2);
    margin-bottom: 16px;
    font-weight: 500;
    box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

/* 事件项样式 */
.event-item,
.facility-item {
    padding: 12px 14px;
    margin-bottom: 10px;
    background: white;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: 1px solid #e8eaf0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
}

.event-item:hover,
.facility-item:hover {
    background: linear-gradient(135deg, #fff 0%, #f8f9fb 100%);
    border-color: #1890ff;
    box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
    transform: translateX(4px);
}

.event-item:last-child,
.facility-item:last-child {
    margin-bottom: 0;
}

.event-name,
.facility-name {
    font-size: 14px;
    font-weight: 500;
    color: #2c3e50;
    margin-bottom: 4px;
}

.event-time {
    font-size: 12px;
    color: #8c8c8c;
    display: flex;
    align-items: center;
    gap: 4px;
}

.event-time::before {
    content: '🕒';
    font-size: 11px;
}

/* 关闭按钮样式 */
.close-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 247, 250, 0.9) 100%);
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    color: #666;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.close-btn:hover {
    background: linear-gradient(135deg, #ff5722 0%, #e64a19 100%);
    color: white;
    transform: rotate(90deg) scale(1.1);
    box-shadow: 0 4px 12px rgba(255, 87, 34, 0.3);
}

/* 状态详情容器样式 */
.states-container {
    position: absolute;
    top: 20px;
    left: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: calc(100% - 40px);
    overflow-y: auto;
    z-index: 999;
    width: 400px;
}

.states-scroll-content {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.state-detail-card {
    position: relative;
    /* background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 251, 252, 0.98) 100%); */
    border-radius: 16px;
    /* padding: 20px; */
    min-width: 320px;
    max-width: 400px;
    /* box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05); */
    /* backdrop-filter: blur(20px); */
    /* border: 1px solid rgba(255, 255, 255, 0.8); */
    animation: fadeInUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.state-close-btn {
    user-select: none;
    position: absolute;
    top: 12px;
    right: 12px;
    width: 28px;
    height: 28px;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 247, 250, 0.9) 100%);
    border: 1px solid rgba(0, 0, 0, 0.06);
    color: #666;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    line-height: 1;
}

.state-close-btn:hover {
    background: linear-gradient(135deg, #ff5722 0%, #e64a19 100%);
    color: white;
    transform: rotate(90deg) scale(1.1);
    box-shadow: 0 4px 12px rgba(255, 87, 34, 0.3);
}

/* 状态树样式 */
.state-tree {
    position: relative;
    padding-left: 12px;
    margin-top: 16px;
}

.state-tree-root {
    margin-bottom: 20px;
}

.state-tree-node {
    position: relative;
}

.state-item {
    position: relative;
    margin-bottom: 12px;
    cursor: pointer;
    padding: 10px 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: 8px;
    background: white;
    border: 1px solid #e8eaf0;
}

.state-item:hover {
    background: linear-gradient(135deg, #f8f9fb 0%, #fff 100%);
    border-color: #1890ff;
    box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
    transform: translateX(2px);
}

.state-item.active {
    background: linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(9, 109, 217, 0.05) 100%);
    border-color: #1890ff;
    box-shadow: 0 4px 12px rgba(24, 144, 255, 0.2);
}

/* 状态点样式 */
.state-dot {
    position: absolute;
    left: -26px;
    top: 16px;
    width: 12px;
    height: 12px;
    background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
    border-radius: 50%;
    border: 2px solid white;
    box-shadow: 0 2px 8px rgba(24, 144, 255, 0.4);
}

/* contain关系的状态点样式 */
.state-dot.contain {
    background: linear-gradient(135deg, #722ed1 0%, #531dab 100%);
    box-shadow: 0 2px 8px rgba(114, 46, 209, 0.4);
}

/* nextState关系的状态点样式 */
.state-dot.next {
    background: linear-gradient(135deg, #13c2c2 0%, #08979c 100%);
    box-shadow: 0 2px 8px rgba(19, 194, 194, 0.4);
}

.state-time {
    font-size: 12px;
    color: #8c8c8c;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 4px;
}

.state-time::before {
    content: '🕒';
    font-size: 11px;
}

.state-desc {
    font-size: 14px;
    color: #2c3e50;
    line-height: 1.6;
    font-weight: 500;
}

/* 子状态和下一个状态的容器 */
.state-children, .state-next {
    position: relative;
    margin-left: 20px;
    padding-left: 20px;
}

/* 分支线样式 */
.state-child-branch, .state-next-branch {
    position: relative;
    margin-bottom: 10px;
}

/* 连接线样式 */
.state-branch-line {
    position: absolute;
    left: -20px;
    top: 0;
    width: 20px;
    height: 20px;
    border-left: 2px solid #d9d9d9;
    border-bottom: 2px solid #d9d9d9;
    border-radius: 0 0 0 4px;
}

/* contain关系的连接线 */
.state-branch-line.contain {
    border-color: #722ed1;
}

/* nextState关系的连接线 */
.state-branch-line.next {
    border-color: #13c2c2;
    height: 40px;
    border-bottom: none;
    border-left: 2px solid #13c2c2;
}

/* 子状态样式 */
.state-item.child-state {
    border-left: 3px solid #722ed1;
}

/* 下一个状态样式 */
.state-item.next-state {
    border-left: 3px solid #13c2c2;
}

/* 响应式滚动条美化 */
.entity-details::-webkit-scrollbar,
.states-container::-webkit-scrollbar {
    width: 6px;
}

.entity-details::-webkit-scrollbar-track,
.states-container::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 3px;
}

.entity-details::-webkit-scrollbar-thumb,
.states-container::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
}

.entity-details::-webkit-scrollbar-thumb:hover,
.states-container::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.3);
}
</style>
