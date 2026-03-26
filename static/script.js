//Form submit handle 

document.getElementById('cropForm')
.addEventListener('submit', function(event){
    event.preventDefault();

    

     //Input Data Cllect

      const data = {
          nitrogen: document.getElementById('nitrogen').value,
         phosphorus: document.getElementById('phosphorus').value,
          potassium: document.getElementById('potassium').value,
         temperature: document.getElementById('temperature').value,
         humidity: document.getElementById('humidity').value,
         pH: document.getElementById('pH').value,
         rainfall: document.getElementById('rainfall').value,
        };



     // Flask API Request Send


     fetch('/predict', {
         method: 'POST',
         headers: {
              'Content-Type': 'application/json'
            },
         body: JSON.stringify(data)
        })
     .then(response => response.json())
     .then(result => {


     // Result Show

     const resultDiv = document.getElementById('result');
     resultDiv.style.display = 'block';
    resultDiv.innerHTML = "☘ Recommended Crop: " + result.crop;
       } )
     .catch(error => {
         console.error('error:', error);
        });
});






