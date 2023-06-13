var DEFAULT_LANGUAGE = 'en';
function getDefaultLanguage() {
  return DEFAULT_LANGUAGE;
}

/**
 * Get translation by key:value
 */
var translationsJson = [];
$.getTranslation = function(name, params, count) {
  if(count>1) {
    name += "_PLURAL";
  }
  var translated = '';
  if (translationsJson.length == 0 || translationsJson[name] == null) {
    translated = name;
  }
  else {
    translated = translationsJson[name];
  }

  // replace placeholders
  for (var key in params) {
    //console.log(key + ":" + params[key]);
    translated = translated.replace('@@' + key + '@@', params[key]);
  }

  //console.log(translationsJson[name]);
  return translated;
}

var Translate = React.createClass({
  render: function() {
    var counter = 0;
    if(this.props.counter != null) {
      counter = this.props.counter;
    }
    var placeholders = {};
    if(this.props.placeholders != null) {
      placeholders = this.props.placeholders;
    }

    return (
      <span>{$.getTranslation(this.props.content, placeholders, counter)}</span>
    );
  }
});

var LocaleSwitcher = React.createClass({
  handleOnChange: function(e) {
    this.setState({lang: e.target.value});     
    this.props.onChangingLanguage({lang: e.target.value});
  },
  getInitialState: function() {
    return {lang: this.props.lang};
  },
  render: function() {
    var divStyle = {
      display: 'inline-block',
      'vertical-align': 'middle',
      'margin-right': '30px'
    };
    return (
      <div style={divStyle}>
        <span><Translate content="switch locale" placeholders={{}} />:</span>

        <select className="locale" defaultValue={getDefaultLanguage()} onChange={this.handleOnChange}>
          <option value="en">en</option>
          <option value="us">us</option>
          <option value="de">de</option>
          <option value="it">it</option>
        </select>
      </div>
    );
  }
});

var LoadingInfo = React.createClass({
  render: function() {
    var divStyle = {
      display: 'inline-block',
      'vertical-align': 'middle'
    };
    return (
      <div style={divStyle}>
        <div>- <Translate content="Time elapsed parsing @@lang@@.json: @@timelapsed@@ms" placeholders={{"lang": this.props.lang, timelapsed:this.props.timelapsed}} /></div>
        <div>- <Translate content="@@lang@@.json contains @@length@@ element" placeholders={{"lang":this.props.lang, "length":this.props.length}} counter={this.props.length} /></div>
      </div>
    );
  }
});

var Greeter = React.createClass({
  render: function() {
    //return <Translate {...this.props} content="example.greeting" />;
    return (
      <h3>
        <Translate content="example.greeting" placeholders={{"name": this.props.name}} />
      </h3>
    );
  }
});

var Greeter2 = React.createClass({
  render: function() {
    //return <Translate {...this.props} content="example.greeting" />;
    return (
      <span>
        <Translate content="second greeting" placeholders={{object: this.props.object}} />
      </span>
    );
  }
});

var Container = React.createClass({
  loadTranslations: function(lang) {
    $.ajax({
      url: lang.lang + '.json',
      dataType: 'text',
      cache: false,
      success: function(data) {
        var start = Date.now();
        translationsJson = JSON.parse(data);
        //translationsJson = data[0];
	var end = Date.now();
	var count = 0;
	Object.keys(translationsJson).forEach(function (key) {
	    count++;
	});
        this.setState({change: this.props.change+1, timelapsed: end - start, lang: lang.lang, length: count});
      }.bind(this),
      error: function(xhr, status, err) {
        console.error(this.props.url, status, err.toString());
        translationsJson = [];
        this.setState({change: this.props.change+1});
      }.bind(this)
    });
  },
  getInitialState: function() {
    return {data:[], change: true};
  },
  componentDidMount: function() {
    this.loadTranslations({lang: getDefaultLanguage()});
    this.setState({change: this.props.change + 1});
  },
  render: function() {
    return (
      <div>
        <br/>

        <LocaleSwitcher onChangingLanguage={this.loadTranslations}/>
        
        <LoadingInfo length={this.state.length} lang={this.state.lang} timelapsed={this.state.timelapsed} />

        <br/><br/>

        <Greeter name="SUSE" />
        <Greeter2 object={$.getTranslation("object", {}, 1)} />

        <br/><br/>

        <Greeter name="SUSE" />
        <Greeter2 object={$.getTranslation("object", {}, 3)} />

      </div>
    );
  }
});

ReactDOM.render(
  <Container />,
  document.getElementById('content')
);
