import React, { useEffect, useRef } from 'react';
import { 
  select, 
  forceSimulation, 
  forceLink, 
  forceManyBody, 
  forceCenter, 
  forceCollide, 
  zoom as d3Zoom, 
  drag as d3Drag, 
  Simulation 
} from 'd3';
import { MemoryNode } from '../../types';
import { MEMORY_COLORS } from '../../constants';

interface GraphViewProps {
  nodes: MemoryNode[];
  onClose: () => void;
}

const GraphView: React.FC<GraphViewProps> = ({ nodes, onClose }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || nodes.length === 0) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    // Clear previous
    select(svgRef.current).selectAll("*").remove();

    const svg = select(svgRef.current)
      .attr("viewBox", [0, 0, width, height]);

    // Construct links based on connection IDs
    const links: any[] = [];
    const nodesMap = new Map(nodes.map(n => [n.id, n]));
    
    nodes.forEach(node => {
        node.connections.forEach(targetId => {
            if (nodesMap.has(targetId)) {
                // Prevent duplicate links
                const linkId = [node.id, targetId].sort().join('-');
                if (!links.find(l => [l.source, l.target].sort().join('-') === linkId)) {
                   links.push({ source: node.id, target: targetId });
                }
            }
        });
    });

    const simulation = forceSimulation(nodes as any)
      .force("link", forceLink(links).id((d: any) => d.id).distance(100))
      .force("charge", forceManyBody().strength(-300))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collide", forceCollide().radius(30));

    // Arrows
    svg.append("defs").selectAll("marker")
      .data(["end"])
      .enter().append("marker")
      .attr("id", String)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 25)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#475569");

    const link = svg.append("g")
      .attr("stroke", "#475569")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", 1.5);

    const node = svg.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => 5 + (d.importance * 10))
      .attr("fill", (d) => MEMORY_COLORS[d.level])
      .attr("cursor", "pointer")
      .call(drag(simulation) as any);

    const label = svg.append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .attr("dx", 15)
        .attr("dy", 4)
        .text((d) => d.label)
        .attr("fill", "#cbd5e1")
        .attr("font-size", "10px")
        .style("pointer-events", "none")
        .style("user-select", "none");

    node.append("title")
      .text(d => `${d.label}\n${d.content.substring(0, 50)}...`);

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node
        .attr("cx", (d: any) => d.x)
        .attr("cy", (d: any) => d.y);

      label
        .attr("x", (d: any) => d.x)
        .attr("y", (d: any) => d.y);
    });

    // Zoom
    const zoomBehavior = d3Zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
            svg.selectAll("g").attr("transform", event.transform);
        });

    svg.call(zoomBehavior as any);

    return () => {
      simulation.stop();
    };
  }, [nodes]);

  // Drag utility
  const drag = (simulation: Simulation<any, undefined>) => {
    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }
    
    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }
    
    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }
    
    return d3Drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);
  }

  return (
    <div ref={containerRef} className="absolute inset-0 z-10 bg-slate-950/95 backdrop-blur-sm flex flex-col">
        <div className="absolute top-4 right-4 z-20 flex gap-2">
            <div className="bg-slate-900/80 p-2 rounded border border-slate-700 text-xs text-slate-300">
                <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-blue-500"></div> Working</span>
                <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-green-500"></div> Session</span>
                <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-orange-500"></div> Episodic</span>
                <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-purple-500"></div> Semantic</span>
            </div>
            <button 
                onClick={onClose}
                className="bg-slate-800 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors border border-slate-700"
            >
                Close Graph
            </button>
        </div>
        <svg ref={svgRef} className="w-full h-full cursor-move"></svg>
    </div>
  );
};

export default GraphView;