// Official modular API: https://echarts.apache.org/handbook/en/basics/import/
import { init, use, graphic } from 'echarts/core'
import { LineChart, HeatmapChart, LinesChart, ScatterChart, CustomChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, VisualMapComponent, GraphicComponent, AriaComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, HeatmapChart, LinesChart, ScatterChart, CustomChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, VisualMapComponent, GraphicComponent, AriaComponent, MarkLineComponent, CanvasRenderer])

export { init, graphic }
