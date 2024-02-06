"use strict";

const useEffect = React.useEffect;
const useState = React.useState;
const useRef = React.useRef;
const useReducer = React.useReducer;
const ROOT_CMD = "spt.modules.workflow.apps.Resource.lib";

const Chart = props => {
  const [loading, set_loading] = useState(true);
  const [name, set_name] = useState("chart" + Math.floor(Math.random() * 100000));
  useEffect(() => {
    init();
  }, []);
  const init = () => {
    let container = document.getElementById(name);
    if (!container) {
      setTimeout(() => {
        init();
      }, 250);
    }
    let title = props.title || "";
    let subtitle = props.subtitle || "";
    let series = props.series || [];
    let data = props.data || [];
    let options = {
      container: container,
      autoSize: true,
      title: {
        text: title
      },
      subtitle: {
        text: subtitle
      },
      legend: {
        position: "bottom"
      },
      data: data,
      series: series
    };
    let axes = props.axes;
    if (axes) {
      options["axes"] = axes;
    }
    let chart = agCharts.AgChart.create(options);
    set_loading(false);
  };
  return React.createElement("div", null, loading && React.createElement("div", null, "Loading ..."), !loading && React.createElement("div", {
    id: name,
    style: {
      height: "calc(100% - 50px)"
    }
  }));
};
spt.react.Chart = Chart;