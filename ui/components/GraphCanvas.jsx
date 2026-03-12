'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';
import LiveProgress from '@/components/LiveProgress';

const NODE_LIMIT = 200;

function nodeColor(topicCoverage) {
  if (topicCoverage === 'your') return '#22c55e';
  if (topicCoverage === 'competitor') return '#ef4444';
  return '#3b82f6';
}

export default function GraphCanvas() {
  const containerRef = useRef(null);
  const rendererRef = useRef(null);
  const { runId } = useRun();
  const [edgeThreshold, setEdgeThreshold] = useState(0);
  const [zoomLevel, setZoomLevel] = useState('topics');

  const { data: graphData, loading: graphLoading, error: graphError } = useApiData('/topic-graph', runId, { deps: [runId] });
  const { data: coverageData, loading: coverageLoading, error: coverageError } = useApiData('/coverage', runId, { deps: [runId] });
  const { data: runs } = useApiData('/runs');
  
  const loading = graphLoading || coverageLoading;
  const error = graphError || coverageError;

  const currentRun = (Array.isArray(runs) ? runs : runs?.runs)?.find(r => String(r.id) === String(runId));
  const isRunning = currentRun?.status === 'running';

  const coverageMap = useRef({});

  const cleanup = () => {
    if (rendererRef.current) {
      rendererRef.current.kill();
      rendererRef.current = null;
    }
  };

  useEffect(() => {
    if (loading || error || !graphData || !containerRef.current) return;
    cleanup();

    const rawCoverage = coverageData && typeof coverageData === 'object' ? coverageData : {};
    coverageMap.current = Object.entries(rawCoverage).reduce((acc, [topicId, data]) => {
      const sorted = [...(data || [])].sort((a, b) => (b.article_count || 0) - (a.article_count || 0));
      if (!sorted.length) {
        acc[topicId] = 'mixed';
      } else if (sorted[0]?.domain?.includes('you')) {
        acc[topicId] = 'your';
      } else if (sorted.length > 1 && sorted[0].article_count === sorted[1].article_count) {
        acc[topicId] = 'mixed';
      } else {
        acc[topicId] = 'competitor';
      }
      return acc;
    }, {});

    const graph = new Graph();
    const trimmedNodes = (graphData?.nodes || []).slice(0, NODE_LIMIT);
    const nodeSet = new Set(trimmedNodes.map((n) => String(n.topic_id || n.id)));

    trimmedNodes.forEach((node) => {
      const nodeId = String(node.topic_id || node.id);
      graph.addNode(nodeId, {
        label: node.topic_name || node.label,
        size: node.size || 4,
        color: nodeColor(coverageMap.current[nodeId])
      });
    });

    (graphData?.edges || []).forEach((edge) => {
      if (!nodeSet.has(String(edge.source)) || !nodeSet.has(String(edge.target))) return;
      if ((edge.weight || 0) < edgeThreshold) return;
      const key = `${edge.source}-${edge.target}`;
      if (!graph.hasEdge(key)) {
        graph.addEdgeWithKey(key, String(edge.source), String(edge.target), {
          size: edge.weight || 1,
          color: '#64748b'
        });
      }
    });

    forceAtlas2.assign(graph, { iterations: 100, settings: { gravity: 1 } });

    const renderer = new Sigma(graph, containerRef.current);
    renderer.on('clickNode', ({ node }) => {
      const selectedAttrs = graph.getNodeAttributes(node);
      graph.forEachNode((n) => {
        const connected = graph.neighbors(node).includes(n) || n === node;
        graph.setNodeAttribute(n, 'size', n === node ? (selectedAttrs.size || 4) * 1.8 : 3);
        graph.setNodeAttribute(n, 'color', connected ? graph.getNodeAttribute(n, 'color') : '#1e293b');
      });
      window.dispatchEvent(new CustomEvent('topicSelected', { detail: { id: node, ...selectedAttrs } }));
      renderer.refresh();
    });

    renderer.getCamera().on('updated', () => {
      const ratio = renderer.getCamera().ratio;
      if (ratio > 1.6) setZoomLevel('clusters');
      else if (ratio > 0.7) setZoomLevel('topics');
      else setZoomLevel('articles');
    });

    rendererRef.current = renderer;

    return () => {
      cleanup();
    };
  }, [graphData, coverageData, runId, edgeThreshold, loading, error]);

  const zoomLabel = useMemo(() => `Zoom detail: ${zoomLevel}`, [zoomLevel]);

  return (
    <div className="space-y-4">
      {runId && isRunning && <LiveProgress runId={runId} />}
      
      <section className="panel p-3">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-semibold">Topic Universe Graph</h2>
          <p className="text-xs text-slate-400">{zoomLabel}</p>
        </div>
        <div className="mb-2 flex items-center gap-2 text-sm">
          <label htmlFor="edge-threshold">Edge threshold</label>
          <input
            id="edge-threshold"
            type="range"
            min="0"
            max="10"
            value={edgeThreshold}
            onChange={(event) => setEdgeThreshold(Number(event.target.value))}
          />
          <span>{edgeThreshold}</span>
        </div>
        {loading && <p className="text-sm text-slate-400">Loading graph data...</p>}
        {error && <p className="text-sm text-red-300">API unavailable</p>}
        <div ref={containerRef} className="h-[560px] w-full rounded bg-slate-950" />
      </section>
    </div>
  );
}
