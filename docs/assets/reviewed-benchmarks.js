/* Only accepted evidence reaches this view; raw strings are always text nodes. */
window.renderReviewedBenchmarks = (container, paper) => {
  const cells = paper.reviewed_benchmark_cells || [];
  container.replaceChildren();
  if (!cells.length) return;
  const heading = document.createElement('h2');
  heading.className = 'font-semibold'; heading.textContent = 'Reviewed source table cells';
  const note = document.createElement('p'); note.className = 'text-sm text-slate-500';
  note.textContent = 'Selected cells checked against this paper. Method labels may refer to baselines. Different datasets and protocols are not directly comparable; this is not a leaderboard.';
  container.append(heading, note);
  const wrapper = document.createElement('div'); wrapper.className = 'overflow-x-auto max-w-full';
  wrapper.tabIndex = 0; wrapper.setAttribute('role','region'); wrapper.setAttribute('aria-label','Reviewed benchmark cells; scroll horizontally for all columns');
  const table = document.createElement('table');table.className = 'text-xs border-collapse w-full my-3';
  const caption = document.createElement('caption');caption.className='text-left';caption.textContent=`${cells.length} accepted source cells`;table.appendChild(caption);
  const head = document.createElement('thead');const headers = document.createElement('tr');
  for (const label of ['Dataset / protocol','Source method','Metric','Value','Unit','Source / review']) {
    const th = document.createElement('th');th.scope='col';th.textContent=label;th.className='text-left p-2 border-b';headers.appendChild(th);
  }
  head.appendChild(headers);table.appendChild(head);
  const body=document.createElement('tbody');
  for(const cell of cells){
    const row=document.createElement('tr');
    for(const value of [`${cell.dataset}\n${cell.split}`,cell.method,cell.metric,cell.value,cell.unit]){
      const td=document.createElement('td');td.textContent=value;td.className='p-2 border-b align-top whitespace-pre-line';row.appendChild(td);
    }
    const source=document.createElement('td');source.className='p-2 border-b align-top';
    const label=`PDF page ${cell.page}`;
    if(cell.source_url && /^https?:\/\//i.test(cell.source_url)){
      const link=document.createElement('a');link.href=cell.source_url;link.target='_blank';link.rel='noopener';link.className='underline';link.textContent=label;source.appendChild(link);
    }else{source.appendChild(document.createTextNode(label+' (public link unavailable)'));}
    const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Review and source identity';details.appendChild(summary);
    const text=document.createElement('p');text.className='break-all';text.textContent=`Checked by ${cell.reviewed_by} at ${cell.reviewed_at}. PDF SHA256: ${cell.pdf_sha256}. Source bounding box: ${cell.bbox.join(', ')}. Parsed value: ${cell.parsed_value}.`;details.appendChild(text);source.appendChild(details);
    row.appendChild(source);body.appendChild(row);
  }
  table.appendChild(body);wrapper.appendChild(table);container.appendChild(wrapper);
};
